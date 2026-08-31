"""
对话记忆系统 — 管理多轮对话的上下文窗口。

提供会话级短期记忆（最近 N 轮对话），
为 AgentV2 提供上下文窗口支持。

支持 SQLite 持久化：服务重启后对话不丢失。
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from src.storage import DATA_DIR


DB_PATH = DATA_DIR / "memory.db"


# ---------------------------------------------------------------------------
# 系统提示词
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是 AI Research Agent，一个专业的实验记录智能助手。

你可以帮助用户：
1. 搜索和分析历史实验记录（支持关键词搜索和语义搜索）
2. 在知识图谱中查找实体和关系
3. 对比不同实验的参数和结果
4. 分析实验趋势和摘要
5. 生成实验复盘报告
6. 分析报错原因并给出解决建议

请始终基于已有数据进行回答，不要编造信息。如果找不到相关数据，请诚实说明。
用中文回答用户问题，回答要简洁专业。
"""


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ConversationTurn:
    """单轮对话。"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class ConversationSession:
    """对话会话。"""
    session_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    tenant_id: str = ""  # 匿名租户标识，用于公网多用户隔离

    # 持久化回调（由 MemoryManager 注入）
    _on_turn_added: Callable | None = field(default=None, repr=False)
    _on_last_active_updated: Callable | None = field(default=None, repr=False)

    def add_message(self, role: str, content: str, metadata: dict | None = None):
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.turns.append(turn)
        self.last_active = time.time()

        # 持久化：写入新 turn + 更新 last_active
        if self._on_turn_added:
            self._on_turn_added(self.session_id, turn)
        if self._on_last_active_updated:
            self._on_last_active_updated(self.session_id, self.last_active)

    def get_context_window(self, max_turns: int = 20) -> list[dict]:
        """获取最近的 N 轮对话作为上下文窗口（OpenAI messages 格式）。"""
        system_turns = [t for t in self.turns if t.role == "system"]
        non_system = [t for t in self.turns if t.role != "system"]
        recent = non_system[-max_turns:]

        result = []
        for t in system_turns:
            result.append({"role": t.role, "content": t.content})
        for t in recent:
            result.append({"role": t.role, "content": t.content})

        return result

    @property
    def turn_count(self) -> int:
        return len([t for t in self.turns if t.role in ("user", "assistant")])

    def to_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


# ---------------------------------------------------------------------------
# SQLite 持久化层
# ---------------------------------------------------------------------------

class _SQLiteStore:
    """SQLite 存储层 — 管理会话和对话轮次的持久化。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        # 先建表（幂等，旧库已存在时 CREATE TABLE 为 no-op）
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                last_active REAL NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );
        """)
        # 迁移：旧库可能没有 tenant_id 列，必须在建索引前补列，否则
        # CREATE INDEX ... ON sessions(tenant_id) 会因列不存在而失败、
        # 导致后续迁移永远不执行。
        try:
            self._conn.execute(
                "ALTER TABLE sessions ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''"
            )
        except Exception:
            pass
        # 建索引（此时 tenant_id 已确保存在）
        self._conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON sessions(tenant_id);
        """)
        self._conn.commit()

    def save_session(self, session_id: str, created_at: float, last_active: float, tenant_id: str = ""):
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, created_at, last_active, tenant_id) VALUES (?, ?, ?, ?)",
            (session_id, created_at, last_active, tenant_id),
        )
        self._conn.commit()

    def save_turn(self, session_id: str, turn: ConversationTurn):
        self._conn.execute(
            "INSERT INTO turns (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, turn.role, turn.content, turn.timestamp,
             json.dumps(turn.metadata, ensure_ascii=False)),
        )
        self._conn.commit()

    def update_last_active(self, session_id: str, last_active: float):
        self._conn.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (last_active, session_id),
        )
        self._conn.commit()

    def delete_session(self, session_id: str):
        self._conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self._conn.commit()

    def load_all_sessions(self) -> list[ConversationSession]:
        """从 SQLite 加载所有会话及其对话轮次。"""
        rows = self._conn.execute(
            "SELECT session_id, created_at, last_active, tenant_id FROM sessions ORDER BY last_active DESC"
        ).fetchall()

        sessions = []
        for row in rows:
            session = ConversationSession(
                session_id=row["session_id"],
                created_at=row["created_at"],
                last_active=row["last_active"],
            )
            session.tenant_id = row["tenant_id"] or ""
            turn_rows = self._conn.execute(
                "SELECT role, content, timestamp, metadata FROM turns WHERE session_id = ? ORDER BY id",
                (row["session_id"],),
            ).fetchall()
            for tr in turn_rows:
                try:
                    meta = json.loads(tr["metadata"])
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                session.turns.append(ConversationTurn(
                    role=tr["role"],
                    content=tr["content"],
                    timestamp=tr["timestamp"],
                    metadata=meta,
                ))
            sessions.append(session)

        return sessions

    def close(self):
        self._conn.close()


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """记忆管理器 — 管理所有活跃会话。

    内存 + SQLite 双层存储：
    - 内存缓存保证读取速度
    - SQLite 持久化保证重启不丢数据

    公网展示（DEMO_READONLY）下按 tenant_id 隔离：每个浏览器一个匿名租户，
    会话列表/历史/删除都限定在自己的租户内，淘汰也只清理同租户最旧的会话，
    避免陌生人串台、互不挤压。
    """

    def __init__(self, max_sessions_per_tenant: int = 20, db_path: Path | None = None):
        self.active_sessions: dict[str, ConversationSession] = {}
        self._session_tenant: dict[str, str] = {}  # session_id -> tenant_id
        self.max_sessions_per_tenant = max_sessions_per_tenant

        # 初始化 SQLite 存储
        self._store = _SQLiteStore(db_path or DB_PATH)
        self._load_from_db()

    def _load_from_db(self):
        """启动时从 SQLite 恢复所有会话到内存。"""
        sessions = self._store.load_all_sessions()
        for session in sessions:
            self._inject_callbacks(session)
            self.active_sessions[session.session_id] = session
            self._session_tenant[session.session_id] = session.tenant_id

    def _inject_callbacks(self, session: ConversationSession):
        """为会话注入持久化回调函数。"""
        session._on_turn_added = self._store.save_turn
        session._on_last_active_updated = self._store.update_last_active

    def create_session(self, tenant_id: str = "") -> str:
        """创建新的对话会话，返回 session_id。"""
        # 仅清理同租户最旧的会话，不影响其他租户
        tenant_sids = [sid for sid, t in self._session_tenant.items() if t == tenant_id]
        if len(tenant_sids) >= self.max_sessions_per_tenant:
            self._cleanup_old_sessions(tenant_id)

        session_id = f"session-{uuid.uuid4().hex[:12]}"
        session = ConversationSession(session_id=session_id, tenant_id=tenant_id)
        self._inject_callbacks(session)

        # 注入 system prompt（会触发持久化）
        session.add_message("system", SYSTEM_PROMPT)

        # 持久化 session 元数据
        self._store.save_session(session_id, session.created_at, session.last_active, tenant_id)

        self.active_sessions[session_id] = session
        self._session_tenant[session_id] = tenant_id
        return session_id

    def get_session(self, session_id: str, tenant_id: str = "") -> ConversationSession | None:
        """获取指定会话（校验租户归属）。"""
        session = self.active_sessions.get(session_id)
        if session and (not tenant_id or self._session_tenant.get(session_id) == tenant_id):
            return session
        return None

    def get_or_create_session(
        self, session_id: str | None, tenant_id: str = ""
    ) -> tuple[str, ConversationSession]:
        """获取或创建会话。返回 (session_id, session)。"""
        if session_id:
            session = self.get_session(session_id, tenant_id)
            if session:
                return session_id, session

        new_id = self.create_session(tenant_id)
        return new_id, self.active_sessions[new_id]

    def delete_session(self, session_id: str, tenant_id: str = "") -> bool:
        """删除指定会话（校验租户归属，内存 + SQLite）。"""
        if self._session_tenant.get(session_id) != tenant_id:
            return False  # 不属于该租户，拒绝
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        self._store.delete_session(session_id)
        self._session_tenant.pop(session_id, None)
        return True

    def list_sessions(self, tenant_id: str = "") -> list[dict]:
        """列出指定租户的活跃会话摘要。"""
        return [
            s.to_summary()
            for sid, s in self.active_sessions.items()
            if self._session_tenant.get(sid) == tenant_id
        ]

    def _cleanup_old_sessions(self, tenant_id: str = ""):
        """清理指定租户最旧的 20% 会话。"""
        tenant_sessions = [
            (sid, self.active_sessions[sid])
            for sid in self.active_sessions
            if self._session_tenant.get(sid) == tenant_id
        ]
        sorted_sessions = sorted(tenant_sessions, key=lambda x: x[1].last_active)
        remove_count = max(1, len(sorted_sessions) // 5)
        for sid, _ in sorted_sessions[:remove_count]:
            self._store.delete_session(sid)
            self.active_sessions.pop(sid, None)
            self._session_tenant.pop(sid, None)


# ---------------------------------------------------------------------------
# 全局实例
# ---------------------------------------------------------------------------

_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取全局 MemoryManager 单例。"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
