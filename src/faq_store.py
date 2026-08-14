"""
报错知识库（FAQ 沉淀）— 产品运营飞轮的核心存储层。

设计目标（面向求职展示的产品叙事）：
- **domain_faq（领域 FAQ）**：从「成功分析」里自动沉淀「报错 → 解决方案」对。
  用户每上传一条带报错日志的实验记录，系统就把其中的错误与对应解法
  抽取成知识条目；后续相似报错再出现时，可直接复用历史解法，
  形成「用户报错 → 沉淀 FAQ → 提升下次回答质量」的飞轮。
- **system_error（系统错误）**：分析流水线自身运行失败（I/O、编码、权限等）
  的签名与排查提示，按出现次数排序，用于上传失败时给用户展示「常见问题」。

两者均落 SQLite（faq.db），与对话记忆、实验数据隔离，互不污染。
"""

import json
import re
import sqlite3
import time
from pathlib import Path

from src.storage import DATA_DIR


DB_PATH = DATA_DIR / "faq.db"

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_一-龥]+")


def _tokens(text: str) -> set:
    return set(_TOKEN_RE.findall(text.lower()))


def _norm_signature(error_text: str, error_type: str = "") -> str:
    """为一条领域 FAQ 生成稳定签名（去重键）。"""
    head = " ".join(list(_tokens(error_text))[:14])
    return f"{error_type}|{head}" if error_type else head


# ---------------------------------------------------------------------------
# 存储层
# ---------------------------------------------------------------------------

class FaqStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS domain_faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signature TEXT UNIQUE NOT NULL,
                error_type TEXT NOT NULL DEFAULT '',
                error_text TEXT NOT NULL,
                solution_text TEXT NOT NULL,
                source_record TEXT NOT NULL DEFAULT '',
                count INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS system_error (
                signature TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                hint TEXT NOT NULL DEFAULT '',
                count INTEGER NOT NULL DEFAULT 1,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_domain_sig ON domain_faq(signature);
            CREATE INDEX IF NOT EXISTS idx_domain_count ON domain_faq(count);
        """)
        self._conn.commit()

    # ---- 领域 FAQ（报错 → 解决方案）----

    def add_domain_faq(
        self,
        error_text: str,
        solution_text: str,
        error_type: str = "",
        source_record: str = "",
    ) -> None:
        if not error_text.strip() or not solution_text.strip():
            return
        signature = _norm_signature(error_text, error_type)
        now = time.time()
        try:
            self._conn.execute(
                """INSERT INTO domain_faq
                   (signature, error_type, error_text, solution_text, source_record, count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (signature, error_type, error_text.strip(), solution_text.strip(), source_record, now, now),
            )
        except sqlite3.IntegrityError:
            # 同签名已存在：累加出现次数，若原解法为空则补充
            self._conn.execute(
                """UPDATE domain_faq
                   SET count = count + 1, updated_at = ?,
                       solution_text = CASE WHEN solution_text = '' THEN ? ELSE solution_text END
                   WHERE signature = ?""",
                (now, solution_text.strip(), signature),
            )
        self._conn.commit()

    def list_domain_faq(self, top_k: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT error_type, error_text, solution_text, source_record, count, updated_at "
            "FROM domain_faq ORDER BY count DESC, updated_at DESC LIMIT ?",
            (top_k,),
        ).fetchall()
        return [_row_to_domain(r) for r in rows]

    def search_domain_faq(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip():
            return []
        q_tokens = _tokens(query)
        if not q_tokens:
            return []
        rows = self._conn.execute(
            "SELECT error_type, error_text, solution_text, source_record, count, updated_at FROM domain_faq"
        ).fetchall()
        scored = []
        for r in rows:
            blob = f"{r['error_text']} {r['solution_text']}"
            overlap = len(q_tokens & _tokens(blob))
            if overlap > 0:
                scored.append((overlap, _row_to_domain(r)))
        scored.sort(key=lambda x: (x[0], x[1]["count"]), reverse=True)
        return [d for _, d in scored[:top_k]]

    # ---- 系统错误（运行时失败）----

    def log_system_error(self, signature: str, message: str, hint: str = "") -> None:
        if not signature.strip():
            return
        now = time.time()
        self._conn.execute(
            """INSERT INTO system_error (signature, message, hint, count, first_seen, last_seen)
               VALUES (?, ?, ?, 1, ?, ?)
               ON CONFLICT(signature) DO UPDATE SET
                   count = count + 1,
                   last_seen = ?,
                   message = excluded.message,
                   hint = CASE WHEN system_error.hint = '' THEN excluded.hint ELSE system_error.hint END""",
            (signature, message[:2000], hint, now, now, now),
        )
        self._conn.commit()

    def list_system_errors(self, top_k: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT signature, message, hint, count, last_seen FROM system_error "
            "ORDER BY count DESC, last_seen DESC LIMIT ?",
            (top_k,),
        ).fetchall()
        return [
            {
                "signature": r["signature"],
                "message": r["message"],
                "hint": r["hint"],
                "count": r["count"],
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]

    def get_hint(self, signature: str) -> str:
        row = self._conn.execute(
            "SELECT hint FROM system_error WHERE signature = ?", (signature,)
        ).fetchone()
        return row["hint"] if row else ""

    def domain_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS c FROM domain_faq").fetchone()["c"]

    def close(self):
        self._conn.close()


def _row_to_domain(r: sqlite3.Row) -> dict:
    return {
        "error_type": r["error_type"],
        "error_text": r["error_text"],
        "solution_text": r["solution_text"],
        "source_record": r["source_record"],
        "count": r["count"],
        "updated_at": r["updated_at"],
    }


# ---------------------------------------------------------------------------
# 从分析记录中沉淀 FAQ（飞轮核心）
# ---------------------------------------------------------------------------

def pair_error_solutions(errors: list, solutions: list) -> list[tuple]:
    """将一条记录里的「报错」与「解决方案」做启发式配对。

    errors: list[dict]（error_tool 输出，含 message/type）
    solutions: list[str]（solution_tool 输出）

    策略：对每条报错，选取与其关键词重叠最多的解法；若无重叠但有解法，
    则退化为关联首条解法。返回 [(error_type, error_text, solution_text), ...]
    """
    pairs = []
    if not solutions:
        return pairs
    sol_tokens = [_tokens(s) for s in solutions]
    for err in errors:
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        etype = err.get("type", "") if isinstance(err, dict) else ""
        if not msg.strip():
            continue
        e_tokens = _tokens(msg)
        best_idx, best_overlap = -1, 0
        for i, st in enumerate(sol_tokens):
            overlap = len(e_tokens & st)
            if overlap > best_overlap:
                best_overlap, best_idx = overlap, i
        if best_idx >= 0 and best_overlap > 0:
            pairs.append((etype, msg, solutions[best_idx]))
        else:
            pairs.append((etype, msg, solutions[0]))
    return pairs


def mine_faq_from_record(record: dict, store: "FaqStore") -> int:
    """从一条成功分析出的记录中沉淀领域 FAQ。返回新增/更新的条目数。"""
    errors = record.get("errors") or []
    solutions = record.get("solutions") or []
    if not errors or not solutions:
        return 0
    pairs = pair_error_solutions(errors, solutions)
    source = record.get("id", "") or record.get("source", "")
    added = 0
    for etype, msg, sol in pairs:
        before = store.domain_count()
        store.add_domain_faq(msg, sol, error_type=etype, source_record=source)
        # 用 count 增量近似判断（同一签名累加不视为新增条目）
        added += 1
    return added


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_faq_store: FaqStore | None = None


def get_faq_store() -> FaqStore:
    global _faq_store
    if _faq_store is None:
        _faq_store = FaqStore()
    return _faq_store


def seed_faq_from_records(records_dir: Path | None = None) -> int:
    """启动时从已有 records 播种领域 FAQ（仅当库为空时），让演示开箱即见内容。

    返回播种的条目数。
    """
    store = get_faq_store()
    if store.domain_count() > 0:
        return 0
    records_dir = records_dir or (DATA_DIR / "records")
    if not records_dir.exists():
        return 0
    seeded = 0
    for f in sorted(records_dir.glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        seeded += mine_faq_from_record(rec, store)
    return seeded
