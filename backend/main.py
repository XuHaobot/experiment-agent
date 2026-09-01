import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 公网只读展示模式：true 时禁用所有写接口（上传/新建实验/删除/重建索引），
# 访客只能对话 + 检索种子记录。配置方式：环境变量 DEMO_READONLY=true 或 .env。
DEMO_READONLY = os.getenv("DEMO_READONLY", "false").strip().lower() in ("1", "true", "yes", "on")


def _assert_writable():
    """写接口守卫：只读模式下返回 403。"""
    if DEMO_READONLY:
        raise HTTPException(
            status_code=403,
            detail="当前为演示模式（只读），不支持上传/新建/删除。请在本地实例使用完整功能。",
        )

from src.agent import ExperimentAgent
from src.agent_v2 import AgentV2
from src.graph.builder import build_graph_from_record
from src.graph.query import search_graph
from src.graph.store import save_graph
from src.llm_client import LLMClient
from src.memory import get_memory_manager
from src.reader import read_uploaded_file
from src.storage import (
    DATA_DIR,
    ensure_storage_dirs,
    save_raw_text,
    save_record,
    save_report,
)
from src.tools.report_tool import generate_markdown_report
from src.tools.search_tool import search_records, hybrid_search
from src.tools.data_analysis_tool import evaluate_answer
from src.faq_store import get_faq_store, seed_faq_from_records, mine_faq_from_record
from src.eval_runner import run_eval


ensure_storage_dirs()

# 启动时从已有 records 播种 FAQ 知识库（仅当库为空），让公网演示开箱即见内容。
try:
    seed_faq_from_records()
except Exception:
    pass


def _try_vector_index(record: dict):
    """尝试将记录索引到向量库，静默失败不影响主流程。"""
    try:
        from src.vector_store import get_vector_store
        store = get_vector_store()
        if store.is_ready:
            store.index_record(record)
    except Exception:
        pass  # 向量库不可用时不影响主流程


# ---------------------------------------------------------------------------
# FAQ 知识库（报错沉淀飞轮）辅助函数
# ---------------------------------------------------------------------------

def _mine_faq_from_record(record: dict):
    """成功分析后，从记录中沉淀「报错 → 解决方案」FAQ。静默失败。"""
    try:
        store = get_faq_store()
        mine_faq_from_record(record, store)
    except Exception:
        pass


def _classify_system_error(exc: Exception) -> tuple[str, str]:
    """将运行时异常归类为签名 + 排查提示，用于上传失败时给用户展示常见问题。"""
    msg = str(exc)
    lowered = msg.lower()
    if "permission" in lowered:
        return ("io_permission", "文件写入权限不足，请检查服务端 data 目录权限。")
    if "encode" in lowered or "utf-8" in lowered or "decode" in lowered:
        return ("encoding", "文本编码无法识别，请使用 UTF-8 编码的文件/文本。")
    if "json" in lowered:
        return ("json_write", "记录写入失败：数据结构异常，请检查输入是否包含异常字符。")
    if "out of memory" in lowered or "memory" in lowered:
        return ("oom", "分析过程内存不足，请减小单次输入体积或分批上传。")
    if "timeout" in lowered:
        return ("timeout", "调用大模型超时，请检查网络或稍后重试。")
    return ("unknown", "分析过程发生未知错误，请检查输入长度与格式后重试。")


app = FastAPI(
    title="实验记录整理 Agent API",
    description="结构化实验记录、知识图谱构建、复盘报告生成",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    client = LLMClient.from_env()
    emb = None
    try:
        from src.vector_store import get_vector_store
        emb = get_vector_store().is_ready
    except Exception:
        emb = False
    return {
        "status": "ok",
        "demo_readonly": DEMO_READONLY,
        "llm_configured": client.is_configured,
        "llm_model": client.model if client.is_configured else None,
        "embedding_ready": emb,
    }


@app.get("/api/system/environment")
def get_system_environment():
    """检测本地 Python 运行空间与常用科学计算库安装状态"""
    packages_to_check = [
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scipy", "scipy"),
        ("matplotlib", "matplotlib"),
        ("duckdb", "duckdb"),
        ("pypdf", "pypdf"),
        ("scikit-learn", "sklearn"),
        ("torch", "torch"),
        ("seaborn", "seaborn"),
    ]
    
    pkg_status = {}
    for disp_name, mod_name in packages_to_check:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "installed")
            pkg_status[disp_name] = {
                "installed": True,
                "version": str(ver),
                "module_name": mod_name,
            }
        except ImportError:
            pkg_status[disp_name] = {
                "installed": False,
                "version": None,
                "install_cmd": f"pip install {disp_name}",
            }

    return {
        "python_version": sys.version.split()[0],
        "executable": sys.executable,
        "working_directory": str(PROJECT_ROOT),
        "data_directory": str(DATA_DIR),
        "packages": pkg_status,
    }


@app.get("/api/system/environments")
def list_system_environments():
    """扫描本机所有可用的 Python 虚拟环境 (Conda, Venv, 系统安装)"""
    from backend.integrations.execution.env_manager import env_manager
    envs = env_manager.scan_environments()
    return {"environments": envs, "total": len(envs)}


class InspectEnvRequest(BaseModel):
    python_executable: str
    working_directory: Optional[str] = None


@app.post("/api/system/environments/inspect")
def inspect_environment(req: InspectEnvRequest):
    """深度自检指定 Python 解释器与工作空间的详细包列表和 GPU 支持"""
    from backend.integrations.execution.env_manager import env_manager
    res = env_manager.inspect_environment(
        python_executable=req.python_executable,
        working_directory=req.working_directory,
    )
    return res


class UpdateProjectEnvRequest(BaseModel):
    python_executable: Optional[str] = None
    env_name: Optional[str] = None
    working_directory: Optional[str] = None


@app.get("/api/projects/{project_id}/environment")
def get_project_environment(project_id: str):
    """获取指定科研课题绑定的虚拟环境与工作目录配置"""
    from backend.domain.project import get_project
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "environment": proj.get("environment") or {
            "python_executable": sys.executable,
            "env_name": "Default Venv",
            "working_directory": str(PROJECT_ROOT),
        }
    }


@app.put("/api/projects/{project_id}/environment")
def set_project_environment(project_id: str, req: UpdateProjectEnvRequest):
    """更新指定科研课题绑定的 Python 虚拟环境与工作目录"""
    _assert_writable()
    from backend.domain.project import get_project, update_project
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    env_config = {
        "python_executable": req.python_executable or sys.executable,
        "env_name": req.env_name or "Custom Environment",
        "working_directory": req.working_directory or str(PROJECT_ROOT),
    }

    updated = update_project(project_id, environment=env_config)
    return {"success": True, "project": updated, "environment": env_config}


@app.post("/api/analyze")
async def analyze_upload(file: UploadFile = File(...)):
    """上传实验记录文件，执行完整分析流水线"""
    _assert_writable()
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    try:
        text = await read_uploaded_file_async(file)
        raw_path = save_raw_text(file.filename or "upload", text)

        agent = ExperimentAgent()
        record = agent.analyze(text, source_name=file.filename)

        record_path = save_record(record)
        report_md = generate_markdown_report(record)
        report_path = save_report(record["id"], report_md)

        graph = build_graph_from_record(record)
        graph_path = save_graph(graph)

        # 自动索引到向量库（静默失败，不影响主流程）
        _try_vector_index(record)

        # 飞轮：成功分析后沉淀报错→解决方案 FAQ
        _mine_faq_from_record(record)

        return {
            "record": record,
            "report": report_md,
            "graph": graph,
            "paths": {
                "raw": str(raw_path),
                "record": str(record_path),
                "report": str(report_path),
                "graph": str(graph_path),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        sig, hint = _classify_system_error(e)
        try:
            get_faq_store().log_system_error(sig, str(e), hint)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"{hint}（错误签名：{sig}）")


@app.post("/api/analyze/text")
async def analyze_text(body: dict):
    """分析纯文本内容（无需上传文件）"""
    _assert_writable()
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    try:
        source = body.get("source", "text-input")
        raw_path = save_raw_text(source, text)

        agent = ExperimentAgent()
        record = agent.analyze(text, source_name=source)

        record_path = save_record(record)
        report_md = generate_markdown_report(record)
        report_path = save_report(record["id"], report_md)

        graph = build_graph_from_record(record)
        graph_path = save_graph(graph)

        # 自动索引到向量库
        _try_vector_index(record)

        # 飞轮：成功分析后沉淀报错→解决方案 FAQ
        _mine_faq_from_record(record)

        return {
            "record": record,
            "report": report_md,
            "graph": graph,
            "paths": {
                "raw": str(raw_path),
                "record": str(record_path),
                "report": str(report_path),
                "graph": str(graph_path),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        sig, hint = _classify_system_error(e)
        try:
            get_faq_store().log_system_error(sig, str(e), hint)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"{hint}（错误签名：{sig}）")


@app.post("/api/analyze/batch")
async def analyze_batch(files: List[UploadFile] = File(...)):
    """批量上传分析：一次提交多个实验记录文件，按序执行完整分析流水线。

    返回汇总：total / success / failed 计数 + 每条成功结果 + 失败明细。
    演示模式（DEMO_READONLY）下禁用。
    """
    _assert_writable()
    if not files:
        raise HTTPException(status_code=400, detail="至少需要上传一个文件")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="单次最多上传 50 个文件")

    results = []
    errors = []
    for file in files:
        if not file.filename:
            errors.append({"filename": None, "error": "文件名不能为空"})
            continue
        try:
            text = await read_uploaded_file_async(file)
            raw_path = save_raw_text(file.filename, text)

            agent = ExperimentAgent()
            record = agent.analyze(text, source_name=file.filename)

            record_path = save_record(record)
            report_md = generate_markdown_report(record)
            report_path = save_report(record["id"], report_md)

            graph = build_graph_from_record(record)
            graph_path = save_graph(graph)

            # 自动索引到向量库（静默失败，不影响主流程）
            _try_vector_index(record)

            # 飞轮：成功分析后沉淀报错→解决方案 FAQ
            _mine_faq_from_record(record)

            results.append({
                "filename": file.filename,
                "record": record,
                "report": report_md,
                "graph": graph,
                "paths": {
                    "raw": str(raw_path),
                    "record": str(record_path),
                    "report": str(report_path),
                    "graph": str(graph_path),
                },
            })
        except Exception as e:
            sig, hint = _classify_system_error(e)
            try:
                get_faq_store().log_system_error(sig, str(e), hint)
            except Exception:
                pass
            errors.append({"filename": file.filename, "error": str(e), "hint": hint, "signature": sig})

    return {
        "total": len(files),
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@app.get("/api/records")
def list_records():
    """获取所有历史实验记录摘要"""
    records_dir = DATA_DIR / "records"
    if not records_dir.exists():
        return {"records": [], "total": 0}

    records = []
    for f in sorted(records_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            records.append({
                "id": data.get("id", f.stem),
                "task": data.get("task", ""),
                "dataset": data.get("dataset", ""),
                "model": data.get("model", ""),
                "created_at": data.get("created_at", ""),
                "filename": f.name,
            })
        except (json.JSONDecodeError, KeyError):
            records.append({
                "id": f.stem,
                "task": "",
                "dataset": "",
                "model": "",
                "created_at": "",
                "filename": f.name,
            })

    return {"records": records, "total": len(records)}


@app.get("/api/records/{record_id}")
def get_record(record_id: str):
    """获取单条实验记录详情"""
    records_dir = DATA_DIR / "records"
    candidates = list(records_dir.glob(f"*{record_id}*.json")) if records_dir.exists() else []
    if not candidates:
        raise HTTPException(status_code=404, detail="记录不存在")

    try:
        record = json.loads(candidates[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="记录文件损坏")

    report_path = DATA_DIR / "reports" / f"{candidates[0].stem}.md"
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    return {"record": record, "report": report_text}


@app.get("/api/graph")
def get_graph_list():
    """获取所有知识图谱列表"""
    graph_dir = DATA_DIR / "graph"
    if not graph_dir.exists():
        return {"graphs": [], "total": 0}

    graphs = []
    from pathlib import Path as _Path
    for f in sorted(graph_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        # skip pyvis HTML exports and non-graph files
        if f.name.startswith("graph.html") or Path(f.name).suffix != ".json":
            continue
        graphs.append({
            "filename": f.name,
            "path": str(f),
            "created_at": f.stat().st_mtime,
        })

    return {"graphs": graphs, "total": len(graphs)}


@app.get("/api/graph/{graph_filename}")
def get_graph(graph_filename: str):
    """获取单个知识图谱"""
    graph_path = DATA_DIR / "graph" / graph_filename
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="图谱不存在")

    try:
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="图谱文件损坏")

    return graph_data


@app.get("/api/search")
def search(q: str = "", mode: str = "hybrid"):
    """全局搜索：实验记录 + 知识图谱。

    mode:
      - "keyword"  纯关键词搜索
      - "hybrid"   混合搜索（关键词 + 语义，默认）
    """
    if not q.strip():
        return {"records": [], "graph": [], "query": q, "mode": mode}

    if mode == "hybrid":
        record_results = hybrid_search(q, DATA_DIR / "records")
    else:
        record_results = search_records(q, DATA_DIR / "records")

    graph_results = search_graph(q)

    return {
        "query": q,
        "mode": mode,
        "records": record_results,
        "graph": graph_results,
        "total": len(record_results) + len(graph_results),
    }


async def read_uploaded_file_async(file: UploadFile) -> str:
    content = await file.read()
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()

    text = content.decode("utf-8", errors="replace")

    if suffix == ".json":
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return text

    return text


@app.post("/api/ask")
async def ask_question(body: dict):
    """问答助手：基于实验记录和知识图谱回答用户问题"""
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 搜索相关记录：先整体搜索，若结果少于3条则拆词再搜
    import re as _re

    record_hits = hybrid_search(question, DATA_DIR / "records")
    graph_hits = search_graph(question)

    tokens = _re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", question)

    if len(record_hits) < 3:
        seen_ids = {r["id"] for r in record_hits}
        for token in tokens:
            if len(token) < 2:
                continue
            extra = hybrid_search(token, DATA_DIR / "records")
            for r in extra:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    record_hits.append(r)

    if len(graph_hits) < 3:
        seen_names = {g["name"] for g in graph_hits}
        for token in tokens:
            if len(token) < 2:
                continue
            extra = search_graph(token)
            for g in extra:
                if g["name"] not in seen_names:
                    seen_names.add(g["name"])
                    graph_hits.append(g)

    # 收集上下文
    contexts = []
    for r in record_hits[:3]:
        # hybrid_search 的语义结果可能无 filename，用 id 回查
        filename = r.get("filename", "")
        rec = None
        if filename:
            try:
                rec = json.loads((DATA_DIR / "records" / filename).read_text(encoding="utf-8"))
            except Exception:
                rec = None
        if rec is None:
            # 按 id 模糊查找
            rid = r.get("id", "")
            candidates = list((DATA_DIR / "records").glob(f"*{rid}*.json"))
            if candidates:
                try:
                    rec = json.loads(candidates[0].read_text(encoding="utf-8"))
                except Exception:
                    pass
        if rec:
            contexts.append({
                "type": "record",
                "id": rec.get("id", r.get("id", "")),
                "task": rec.get("task", ""),
                "dataset": rec.get("dataset", ""),
                "model": rec.get("model", ""),
                "errors": rec.get("errors", []),
                "solutions": rec.get("solutions", []),
                "conclusion": rec.get("conclusion", ""),
                "next_step": rec.get("next_step", ""),
            })
        elif r.get("task"):
            # 语义搜索结果可能直接携带摘要字段
            contexts.append({
                "type": "record",
                "id": r.get("id", ""),
                "task": r.get("task", ""),
                "dataset": r.get("dataset", ""),
                "model": r.get("model", ""),
                "snippet": r.get("snippet", ""),
            })

    for g in graph_hits[:5]:
        contexts.append({"type": "graph_entity", "name": g["name"], "kind": g["type"], "summary": g["summary"]})

    # FAQ 知识库增强：检索历史沉淀的「报错 → 解决方案」，让回答随使用持续变好（飞轮）
    try:
        faq_hits = get_faq_store().search_domain_faq(question, top_k=3)
        for faq in faq_hits:
            contexts.append({
                "type": "faq",
                "error_text": faq["error_text"],
                "solution_text": faq["solution_text"],
                "occurrences": faq["count"],
            })
    except Exception:
        pass

    # 构建 prompt
    context_str = json.dumps(contexts, ensure_ascii=False, indent=2)
    prompt = (
        f"你是一个实验记录助手。根据以下历史实验数据回答用户问题。\n\n"
        f"## 历史实验数据\n{context_str}\n\n"
        f"## 用户问题\n{question}\n\n"
        f"请用中文简要回答（不超过300字）。如果数据中找不到相关信息，诚实说明。"
    )

    client = LLMClient.from_env()
    if not client.is_configured:
        return {
            "answer": "LLM 未配置。请在 .env 中设置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL。\n\n以下是搜索到的相关记录供参考:\n\n" +
                      "\n".join(f"- [{c.get('type','')}] {c.get('task',c.get('name',''))}" for c in contexts[:5]),
            "contexts": contexts,
        }

    answer = client.call_llm(prompt)
    if answer.startswith("LLM_"):
        return {"answer": f"LLM 调用失败: {answer}", "contexts": contexts}

    return {"answer": answer, "contexts": contexts}


@app.post("/api/evaluate")
async def evaluate(body: dict):
    """评估 AI 回答质量（LLM-as-Judge，0-10 分）。"""
    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()
    ground_truth = body.get("ground_truth")

    if not question or not answer:
        raise HTTPException(status_code=400, detail="question 和 answer 不能为空")

    result = evaluate_answer(question, answer, ground_truth)
    return result


# ============================================================
# FAQ 知识库 API（报错沉淀飞轮）
# ============================================================

@app.get("/api/faq")
def list_faq():
    """获取 FAQ 知识库概览：领域 FAQ（报错→解决方案）+ 系统常见问题，按出现次数排序。"""
    store = get_faq_store()
    return {
        "domain": store.list_domain_faq(top_k=30),
        "system": store.list_system_errors(top_k=20),
        "domain_count": store.domain_count(),
    }


@app.post("/api/faq/search")
async def search_faq(body: dict):
    """按关键词检索领域 FAQ（报错→解决方案），用于上传失败时给用户的排查提示，以及问答增强。"""
    query = body.get("query", "").strip()
    if not query:
        return {"results": []}
    store = get_faq_store()
    return {"results": store.search_domain_faq(query, top_k=body.get("top_k", 5))}


@app.post("/api/evaluate/run")
async def run_eval_endpoint(body: dict | None = None):
    """评测集自动化回归（LLM-as-Judge + 字段覆盖率）。

    用于「每次改动模型/提示词，自动跑评测集确保指标不降质」的 CI 式回归。
    使用服务端 LLM 配置，会消耗 token，故公网只读模式下禁用。
    """
    _assert_writable()
    dataset_path = (body or {}).get("dataset_path")
    try:
        return run_eval(dataset_path=dataset_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评测运行失败: {e}")


# ============================================================
# AgentV2 Chat API (Function Calling)
# ============================================================

@app.post("/api/chat")
async def chat(body: dict):
    """AgentV2 对话接口（Function Calling 驱动）。

    支持多轮对话：传入 session_id 维持上下文。
    不传 session_id 则自动创建新会话。
    """
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    session_id = body.get("session_id")
    tenant_id = body.get("tenant_id", "")  # 匿名租户隔离（不落盘）
    llm_config = body.get("llm_config")  # BYOK：用户自带 chat Key（不落盘）
    embedding_config = body.get("embedding_config")  # BYOK：用户自带 Embedding Key（不落盘）

    memory = get_memory_manager()
    session_id, session = memory.get_or_create_session(session_id, tenant_id)

    # 获取上下文窗口
    context = session.get_context_window(max_turns=20)
    history_len = len(context)  # 已有的消息数

    # 调用 AgentV2
    agent = AgentV2(max_iterations=5)
    result = agent.chat(
        question,
        conversation_history=context,
        llm_config=llm_config,
        embedding_config=embedding_config,
    )

    # 将本轮新增的对话（含工具调用）记入会话
    conv_messages = result.get("conversation_messages", [])
    for msg in conv_messages[history_len:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        session.add_message(role, content if isinstance(content, str) else str(content))

    return {
        "answer": result["answer"],
        "agent_trace": result["agent_trace"],
        "total_iterations": result["total_iterations"],
        "session_id": session_id,
        "turn_count": session.turn_count,
    }


@app.post("/api/chat/stream")
async def chat_stream(body: dict):
    """AgentV2 流式对话接口（SSE）。

    逐事件返回：
    1. session_id
    2. 工具调用轨迹（每调用一个工具推送一次）
    3. 逐 token 流式推送最终回答
    4. 完整回答
    5. [DONE]
    """
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    session_id = body.get("session_id")
    tenant_id = body.get("tenant_id", "")  # 匿名租户隔离（不落盘）
    llm_config = body.get("llm_config")  # BYOK：用户自带 chat Key（不落盘）
    embedding_config = body.get("embedding_config")  # BYOK：用户自带 Embedding Key（不落盘）

    async def generate():
        import asyncio

        memory = get_memory_manager()
        sid, session = memory.get_or_create_session(session_id, tenant_id)

        # 推送 session_id
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': sid}, ensure_ascii=False)}\n\n"

        # 获取上下文
        context = session.get_context_window(max_turns=20)

        agent = AgentV2(max_iterations=5)

        full_answer = ""
        trace_steps = []

        for event in agent.chat_stream(
            question,
            conversation_history=context,
            llm_config=llm_config,
            embedding_config=embedding_config,
        ):
            event_type = event.get("type")

            if event_type == "trace":
                step = event["step"]
                trace_steps.append(step)
                yield f"data: {json.dumps({'type': 'trace', 'step': step}, ensure_ascii=False, default=str)}\n\n"
                await asyncio.sleep(0)

            elif event_type == "token":
                token = event.get("token", "")
                yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"

            elif event_type == "answer":
                full_answer = event.get("answer", "")
                # 记入会话历史
                session.add_message("user", question)
                session.add_message("assistant", full_answer, metadata={
                    "trace": trace_steps,
                    "iterations": event.get("total_iterations", 0),
                })
                yield f"data: {json.dumps({'type': 'answer', 'answer': full_answer}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================
# Vector Store API
# ============================================================

@app.get("/api/vector-store/stats")
async def vector_store_stats():
    """获取向量库统计信息。"""
    try:
        from src.vector_store import VectorStore
        store = VectorStore()
        if not store.is_ready:
            return {"ready": False, "error": "DASHSCOPE_API_KEY 未配置"}
        return {"ready": True, **store.stats()}
    except Exception as exc:
        return {"ready": False, "error": str(exc)}


@app.post("/api/vector-store/rebuild")
async def rebuild_vector_index():
    """重建向量索引（从 records 目录重新索引所有记录）。"""
    _assert_writable()
    try:
        from src.vector_store import VectorStore
        store = VectorStore()
        if not store.is_ready:
            raise HTTPException(status_code=503, detail="DASHSCOPE_API_KEY 未配置，无法构建向量索引")
        result = store.rebuild_index(DATA_DIR / "records")
        return {"status": "ok", **result, **store.stats()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重建索引失败: {exc}")


@app.post("/api/vector-store/index/{record_id}")
async def index_single_record(record_id: str):
    """将单条记录索引到向量库。"""
    _assert_writable()
    try:
        from src.vector_store import VectorStore
        store = VectorStore()
        if not store.is_ready:
            raise HTTPException(status_code=503, detail="DASHSCOPE_API_KEY 未配置")

        candidates = list((DATA_DIR / "records").glob(f"*{record_id}*.json"))
        if not candidates:
            raise HTTPException(status_code=404, detail="记录不存在")

        record = json.loads(candidates[0].read_text(encoding="utf-8"))
        chunk_count = store.index_record(record)
        return {"status": "ok", "record_id": record_id, "chunks": chunk_count}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"索引失败: {exc}")


# ============================================================
# Session Management API
# ============================================================

@app.get("/api/sessions")
async def list_sessions(tenant_id: str = ""):
    """列出指定租户的活跃对话会话（公网按浏览器隔离）。"""
    memory = get_memory_manager()
    return {"sessions": memory.list_sessions(tenant_id)}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, tenant_id: str = ""):
    """删除指定对话会话（校验租户归属）。"""
    memory = get_memory_manager()
    deleted = memory.delete_session(session_id, tenant_id)
    return {"ok": deleted}


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str, tenant_id: str = ""):
    """获取指定会话的对话历史（校验租户归属）。"""
    memory = get_memory_manager()
    session = memory.get_session(session_id, tenant_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    history = []
    for turn in session.turns:
        entry = {
            "role": turn.role,
            "content": turn.content,
            "timestamp": turn.timestamp,
        }
        # assistant 消息可能携带 agent_trace
        if turn.role == "assistant" and turn.metadata:
            trace = turn.metadata.get("trace")
            if trace:
                entry["agent_trace"] = trace
        history.append(entry)

    return {
        "session_id": session_id,
        "turn_count": session.turn_count,
        "history": history,
    }


# ============================================================
# Experiment Management API
# ============================================================
EXPERIMENTS_DIR = DATA_DIR / "experiments"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENTS_INDEX_FILE = EXPERIMENTS_DIR / "index.json"


def _load_experiments() -> list:
    if not EXPERIMENTS_INDEX_FILE.exists():
        return []
    try:
        return json.loads(EXPERIMENTS_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_experiments(exps: list):
    EXPERIMENTS_INDEX_FILE.write_text(json.dumps(exps, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/experiments")
async def list_experiments():
    experiments = _load_experiments()
    records_dir = DATA_DIR / "records"
    for exp in experiments:
        exp_records = exp.get("record_ids", [])
        exp["recordCount"] = len(exp_records)
    return {"experiments": experiments, "total": len(experiments)}


@app.post("/api/experiments")
async def create_experiment(body: dict):
    _assert_writable()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="实验名称不能为空")
    experiments = _load_experiments()
    import uuid
    new_exp = {
        "id": f"exp-{uuid.uuid4().hex[:10]}",
        "name": name,
        "description": body.get("description", "").strip(),
        "record_ids": [],
        "created_at": body.get("created_at", ""),
    }
    experiments.append(new_exp)
    _save_experiments(experiments)
    return {"experiment": new_exp}


@app.delete("/api/experiments/{exp_id}")
async def delete_experiment(exp_id: str):
    _assert_writable()
    experiments = _load_experiments()
    experiments = [e for e in experiments if e["id"] != exp_id]
    _save_experiments(experiments)
    return {"ok": True}


@app.delete("/api/records/{record_id}")
async def delete_record(record_id: str):
    """删除实验记录及其关联的报告和图谱"""
    _assert_writable()
    import glob as _glob
    records_dir = DATA_DIR / "records"
    deleted = False

    # 查找并删除记录文件
    for f in _glob.glob(str(records_dir / f"*{record_id}*.json")):
        stem = Path(f).stem
        # 删除关联报告
        report_path = DATA_DIR / "reports" / f"{stem}.md"
        if report_path.exists():
            report_path.unlink()
        # 删除关联图谱
        for gf in _glob.glob(str(DATA_DIR / "graph" / f"*{record_id[:15]}*.json")):
            Path(gf).unlink()
        # 删除记录本身
        Path(f).unlink()
        deleted = True

    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 从所有实验中移除此记录
    experiments = _load_experiments()
    for exp in experiments:
        if record_id in exp.get("record_ids", []):
            exp["record_ids"].remove(record_id)
    _save_experiments(experiments)

    return {"ok": True}


@app.post("/api/experiments/{exp_id}/records/{record_id}")
async def add_record_to_experiment(exp_id: str, record_id: str):
    _assert_writable()
    experiments = _load_experiments()
    for exp in experiments:
        if exp["id"] == exp_id:
            if record_id not in exp.setdefault("record_ids", []):
                exp["record_ids"].append(record_id)
            _save_experiments(experiments)
            return {"ok": True}
    raise HTTPException(status_code=404, detail=f"实验 {exp_id} 不存在")


# =============================================================================
# V2 API — Research Project
# =============================================================================

@app.post("/api/projects")
async def create_project(body: dict):
    """新建 Research Project"""
    _assert_writable()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    from backend.domain.project import create_project as _create_project
    project = _create_project(name, body.get("description", ""))
    return project


@app.get("/api/projects")
def list_projects():
    """列出所有 Research Project"""
    from backend.domain.project import list_projects as _list_projects
    projects = _list_projects()
    return {"projects": projects, "total": len(projects)}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """获取单个 Research Project 详情"""
    from backend.domain.project import get_project as _get_project
    project = _get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    return project


@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, body: dict):
    """更新 Project 基本信息"""
    _assert_writable()
    from backend.domain.project import update_project as _update_project
    project = _update_project(
        project_id,
        name=body.get("name"),
        description=body.get("description"),
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    return project


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """删除 Project（不删除关联实验）"""
    _assert_writable()
    from backend.domain.project import delete_project as _delete_project
    ok = _delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project 不存在")
    return {"ok": True}


@app.post("/api/projects/{project_id}/experiments/{record_id}")
async def add_experiment_to_project(project_id: str, record_id: str):
    """将实验记录关联到 Project"""
    _assert_writable()
    from backend.domain.project import add_experiment_to_project as _add_exp
    project = _add_exp(project_id, record_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    return {"ok": True, "project": project}


@app.delete("/api/projects/{project_id}/experiments/{record_id}")
def remove_experiment_from_project(project_id: str, record_id: str):
    """从 Project 解除实验关联并清理实验记录与关联 Runs"""
    _assert_writable()
    from backend.domain.project import remove_experiment_from_project as _remove_exp
    project = _remove_exp(project_id, record_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    
    # 清理 data/records/<record_id>.json
    rec_file = DATA_DIR / "records" / f"{record_id}.json"
    if rec_file.exists():
        try:
            rec_file.unlink()
        except Exception:
            pass

    # 清理关联 runs
    try:
        from backend.domain.run import list_runs, delete_run
        runs = list_runs(record_id)
        for r in runs:
            delete_run(r["id"])
    except Exception:
        pass

    return {"ok": True}


# =============================================================================
# V2 API — Research Question
# =============================================================================

@app.post("/api/projects/{project_id}/questions")
async def add_question(project_id: str, body: dict):
    """向 Project 添加 Research Question"""
    _assert_writable()
    text = (body.get("text") or body.get("question") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="问题内容不能为空")
    from backend.domain.project import add_question as _add_question, get_project as _get_project
    if _get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    question = _add_question(project_id, text)
    return question


@app.delete("/api/projects/{project_id}/questions/{question_id}")
def delete_question(project_id: str, question_id: str):
    """删除 Project 中的 Research Question"""
    _assert_writable()
    from backend.domain.project import delete_question as _delete_question
    ok = _delete_question(project_id, question_id)
    if not ok:
        raise HTTPException(status_code=404, detail="问题不存在")
    return {"ok": True}


# =============================================================================
# V2 API — Hypothesis
# =============================================================================

@app.post("/api/projects/{project_id}/hypotheses")
async def create_hypothesis(project_id: str, body: dict):
    """新建 Hypothesis"""
    _assert_writable()
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="假设标题不能为空")
    from backend.domain.hypothesis import create_hypothesis as _create_hyp
    hyp = _create_hyp(
        project_id=project_id,
        title=title,
        description=body.get("description", ""),
        question_id=body.get("question_id"),
    )
    return hyp


@app.get("/api/projects/{project_id}/hypotheses")
def list_hypotheses(project_id: str):
    """列出 Project 下所有 Hypothesis"""
    from backend.domain.hypothesis import list_hypotheses as _list_hyps
    hyps = _list_hyps(project_id=project_id)
    return {"hypotheses": hyps, "total": len(hyps)}


@app.get("/api/hypotheses/{hypothesis_id}")
def get_hypothesis(hypothesis_id: str):
    """获取单个 Hypothesis 详情"""
    from backend.domain.hypothesis import get_hypothesis as _get_hyp
    hyp = _get_hyp(hypothesis_id)
    if hyp is None:
        raise HTTPException(status_code=404, detail="Hypothesis 不存在")
    return hyp


@app.put("/api/hypotheses/{hypothesis_id}")
async def update_hypothesis(hypothesis_id: str, body: dict):
    """更新 Hypothesis（标题、描述、状态）"""
    _assert_writable()
    from backend.domain.hypothesis import update_hypothesis as _update_hyp
    try:
        hyp = _update_hyp(
            hypothesis_id,
            title=body.get("title"),
            description=body.get("description"),
            status=body.get("status"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if hyp is None:
        raise HTTPException(status_code=404, detail="Hypothesis 不存在")
    return hyp


@app.delete("/api/hypotheses/{hypothesis_id}")
def delete_hypothesis(hypothesis_id: str):
    """删除 Hypothesis"""
    _assert_writable()
    from backend.domain.hypothesis import delete_hypothesis as _delete_hyp
    ok = _delete_hyp(hypothesis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Hypothesis 不存在")
    return {"ok": True}


@app.post("/api/hypotheses/{hypothesis_id}/evidence")
async def add_evidence(hypothesis_id: str, body: dict):
    """向 Hypothesis 添加证据"""
    _assert_writable()
    from backend.domain.hypothesis import add_evidence as _add_evidence
    evidence = _add_evidence(
        hypothesis_id,
        source=body.get("source", ""),
        text=body.get("text", ""),
        supports=body.get("supports", True),
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Hypothesis 不存在")
    return evidence


@app.post("/api/hypotheses/{hypothesis_id}/experiments/{record_id}")
async def link_experiment_to_hypothesis(hypothesis_id: str, record_id: str):
    """将实验关联到 Hypothesis"""
    _assert_writable()
    from backend.domain.hypothesis import link_experiment as _link_exp
    hyp = _link_exp(hypothesis_id, record_id)
    if hyp is None:
        raise HTTPException(status_code=404, detail="Hypothesis 不存在")
    return {"ok": True}


@app.post("/api/projects/{project_id}/hypotheses/suggest")
async def suggest_hypotheses(project_id: str, body: dict):
    """AI 辅助根据 Research Question 建议假设列表"""
    from backend.domain.hypothesis import ai_suggest_hypotheses
    question_text = body.get("question_text", "").strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="question_text 不能为空")
    from backend.domain.project import get_project as _get_project
    project = _get_project(project_id)
    context = project.get("description", "") if project else ""
    suggestions = ai_suggest_hypotheses(question_text, project_context=context)
    return {"suggestions": suggestions}


# =============================================================================
# V2 API — Literature
# =============================================================================

@app.get("/api/literature/search")
def search_literature(q: str = "", source: str = "openalex", limit: int = 8):
    """搜索学术论文（OpenAlex / Semantic Scholar）"""
    if not q.strip():
        return {"papers": [], "query": q, "source": source}
    from backend.domain.literature import search_papers
    papers = search_papers(q.strip(), source=source, limit=limit)
    return {"papers": papers, "query": q, "source": source, "total": len(papers)}


@app.get("/api/literature/paper/{paper_id}")
def get_paper(paper_id: str, source: str = "openalex"):
    """获取论文详情"""
    from backend.domain.literature import get_paper_detail
    paper = get_paper_detail(paper_id, source=source)
    if paper is None:
        raise HTTPException(status_code=404, detail="论文不存在")
    return paper


# =============================================================================
# V2 API — Next Experiment
# =============================================================================

@app.get("/api/projects/{project_id}/next-experiment")
def get_next_experiment_recommendations(project_id: str, max_candidates: int = 3):
    """获取 AI 推荐的下一轮实验候选方案"""
    from backend.domain.project import get_project as _get_project
    if _get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    from backend.domain.next_experiment import recommend_next_experiments
    result = recommend_next_experiments(project_id, max_candidates=max_candidates)
    return result


@app.post("/api/projects/{project_id}/next-experiment/confirm")
async def confirm_next_experiment(project_id: str, body: dict):
    """用户确认候选实验 → 一键创建为正式实验草稿"""
    _assert_writable()
    candidate = body.get("candidate")
    if not candidate:
        raise HTTPException(status_code=400, detail="candidate 不能为空")
    from backend.domain.project import get_project as _get_project
    if _get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project 不存在")
    from backend.domain.next_experiment import create_experiment_from_candidate
    record = create_experiment_from_candidate(project_id, candidate)
    # 也更新 Research Graph
    try:
        from src.graph.builder import build_graph_from_record
        from src.graph.store import save_graph
        graph = build_graph_from_record(record)
        save_graph(graph)
    except Exception:
        pass
    return {"ok": True, "record": record}


@app.post("/api/projects/{project_id}/experiments")
async def create_project_experiment(project_id: str, body: dict):
    """在 Project 内直接创建实验方案"""
    _assert_writable()
    from backend.domain.project import get_project, add_experiment_to_project
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project 不存在")

    import uuid
    from datetime import datetime, timezone
    from src.storage import save_record

    exp_id = f"exp_{uuid.uuid4().hex[:10]}"
    params = body.get("params", {})
    if not isinstance(params, dict):
        params = {"raw": str(params)}

    record = {
        "id": exp_id,
        "task": body.get("task", body.get("name", "New Experiment")),
        "dataset": body.get("dataset", ""),
        "model": body.get("model", ""),
        "params": {
            "original": params,
            "adjusted": {},
            "suggested": {},
        },
        "commands": body.get("commands", []),
        "errors": [],
        "solutions": [],
        "conclusions": body.get("conclusions", body.get("expected_outcome", "")),
        "next_steps": [],
        "source": "Scientific IDE",
        "project_id": project_id,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_record(record)
    add_experiment_to_project(project_id, exp_id)
    return {"ok": True, "record": record}


# =============================================================================
# V2 API — Research Cockpit, Timeline & Research Memory
# =============================================================================

@app.get("/api/projects/{project_id}/cockpit")
def get_project_cockpit(project_id: str):
    """获取 Project 的 Research Cockpit 一站式核心状态"""
    from backend.domain.project import get_project
    from backend.domain.hypothesis import list_hypotheses
    from backend.domain.run import list_runs
    from backend.domain.conclusion import list_conclusions
    from backend.domain.next_experiment import recommend_next_experiments

    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")

    # 1. 核心科学问题
    questions = project.get("questions", [])
    active_question = questions[0]["text"] if questions else None

    # 2. 核心科学假说
    hyps = list_hypotheses(project_id)
    active_hyp = hyps[0] if hyps else None

    # 3. 汇总历史 Runs
    all_runs = []
    exp_ids = project.get("experiment_ids", [])
    for eid in exp_ids:
        all_runs.extend(list_runs(experiment_id=eid))

    best_run = None
    best_acc = -1.0
    for r in all_runs:
        metrics = r.get("metrics", {})
        acc = metrics.get("val_accuracy", metrics.get("accuracy", 0))
        if isinstance(acc, (int, float)) and acc > best_acc:
            best_acc = acc
            best_run = r

    # 4. 证据账本
    concs = list_conclusions(project_id)
    evidence_ledger = []
    for c in concs:
        for ev in c.get("evidence_refs", []):
            evidence_ledger.append({
                "id": ev.get("id"),
                "type": ev.get("type", "run"),
                "snippet": ev.get("snippet", ""),
                "conclusion_id": c.get("id"),
                "stance": "SUPPORT" if c.get("confidence") != "low" else "CONTRADICT",
            })

    # 如果暂无显式证据，从完成的 runs 动态生成真实证据项
    if not evidence_ledger and all_runs:
        for r in all_runs[:4]:
            m = r.get("metrics", {})
            acc = m.get("val_accuracy", m.get("accuracy", 0))
            p = r.get("actual_parameters", {})
            p_k = p.get("k", "N/A")
            acc_str = f"{acc*100:.1f}%" if isinstance(acc, (int, float)) else str(acc)
            is_sup = acc >= 0.8 if isinstance(acc, (int, float)) else True
            evidence_ledger.append({
                "id": r.get("id"),
                "type": "run",
                "snippet": f"k={p_k} 实测准确率达到 {acc_str} (状态: {r.get('status')})",
                "stance": "SUPPORT" if is_sup else "CONTRADICT",
            })

    # 5. Next Research Action 结构化决策
    rec_res = recommend_next_experiments(project_id, max_candidates=1)
    candidates = rec_res.get("candidates", [])
    next_action = candidates[0] if candidates else None

    # 6. 获取科研状态 (Research State)
    from backend.domain.memory import get_project_research_memory
    mem_slice = get_project_research_memory(project_id)
    research_state = mem_slice.get("research_state", {})

    return {
        "project": project,
        "active_question": active_question,
        "active_hypothesis": active_hyp,
        "evidence_ledger": evidence_ledger,
        "next_research_action": next_action,
        "research_state": research_state,
        "cadence": {
            "cycle": f"Cycle #{len(all_runs) + 1:02d}",
            "total_runs": len(all_runs),
            "best_accuracy": f"{best_acc*100:.1f}% ({best_run.get('id')})" if best_run and best_acc >= 0 else "N/A",
            "runtime_total": f"{len(all_runs) * 1.6:.1f} hrs",
        },
    }


@app.get("/api/projects/{project_id}/state")
def get_project_state_route(project_id: str):
    """获取 Project 的当前科研状态 (KNOWN, TRIED, FAILED, UNCERTAINTY, NEXT)"""
    from backend.domain.memory import get_project_research_memory
    mem = get_project_research_memory(project_id)
    return {
        "project_id": project_id,
        "research_state": mem.get("research_state", {}),
        "best_run": mem.get("best_run"),
        "best_accuracy": mem.get("best_accuracy"),
    }


@app.post("/api/experiments/{experiment_id}/runs/import-csv")
def import_csv_to_runs_route(experiment_id: str, body: dict):
    """从 CSV 文本直接批量解析并导入 Runs"""
    csv_text = body.get("csv_text", "").strip()
    if not csv_text:
        raise HTTPException(status_code=400, detail="csv_text 不能为空")
    from backend.domain.run import import_runs_from_csv
    res = import_runs_from_csv(experiment_id, csv_text)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "CSV 导入失败"))
    return res


@app.post("/api/projects/{project_id}/analyses")
def save_analysis_session_route(project_id: str, body: dict):
    """持久化保存 Python 数据分析会话"""
    from backend.domain.analysis import create_analysis_session
    name = body.get("name", "Analysis Session")
    code = body.get("code", "")
    stdout = body.get("stdout", "")
    charts = body.get("charts", [])
    insights = body.get("insights", "")
    exp_id = body.get("experiment_id")
    run_ids = body.get("run_ids", [])
    record = create_analysis_session(
        project_id=project_id,
        name=name,
        code=code,
        stdout=stdout,
        charts=charts,
        insights=insights,
        experiment_id=exp_id,
        run_ids=run_ids,
    )
    return {"ok": True, "analysis": record}


@app.get("/api/projects/{project_id}/analyses")
def list_analysis_sessions_route(project_id: str):
    """列出 Project 下保存的所有 Python 分析会话"""
    from backend.domain.analysis import list_analysis_sessions
    sessions = list_analysis_sessions(project_id)
    return {"project_id": project_id, "analyses": sessions, "total": len(sessions)}


@app.get("/api/projects/{project_id}/graph/trace/{node_id}")
def trace_graph_causality_route(project_id: str, node_id: str):
    """针对图谱中的特定节点进行多跳因果链路双向回溯与前瞻 (Full Bidirectional Lineage)"""
    from backend.domain.conclusion import get_conclusion, list_conclusions
    from backend.domain.run import get_run, list_runs
    from backend.domain.hypothesis import get_hypothesis, list_hypotheses
    from backend.domain.artifact import get_artifact, list_artifacts
    from backend.domain.paper import get_paper, list_project_papers
    from backend.domain.dataset import get_dataset, list_project_datasets

    ancestors = []
    descendants = []
    node_type = "unknown"

    if node_id.startswith("conc_"):
        node_type = "conclusion"
        c = get_conclusion(node_id)
        if c:
            # 1. 直接父级：假说
            if c.get("hypothesis_id"):
                ancestors.append({"id": c["hypothesis_id"], "type": "hypothesis", "title": "Target Hypothesis"})
                h = get_hypothesis(c["hypothesis_id"])
                if h:
                    ancestors.append({"id": "project_rq", "type": "question", "title": "Core Research Question"})
            
            # 2. 直接父级：证据链
            for ev in c.get("evidence_refs", []):
                ev_id = ev.get("id")
                ev_type = ev.get("type", "evidence")
                ancestors.append({"id": ev_id, "type": ev_type, "snippet": ev.get("snippet", "")})
                
                # 多跳追溯：如果证据来自 Artifact
                if ev_type == "artifact":
                    art = get_artifact(ev_id)
                    if art and art.get("source_record_id"):
                        ancestors.append({"id": art["source_record_id"], "type": "run", "title": "Origin Run"})
                        r = get_run(art["source_record_id"])
                        if r and r.get("experiment_id"):
                            ancestors.append({"id": r["experiment_id"], "type": "experiment", "title": "Origin Experiment"})
                
                # 多跳追溯：如果证据来自 Run
                elif ev_type == "run":
                    r = get_run(ev_id)
                    if r and r.get("experiment_id"):
                        ancestors.append({"id": r["experiment_id"], "type": "experiment", "title": "Origin Experiment"})
                
                # 多跳追溯：如果证据来自 Paper
                elif ev_type == "paper":
                    p = get_paper(ev_id)
                    if p:
                        ancestors.append({"id": project_id, "type": "project", "title": f"Literature from Project ({p.get('source', '')})"})
                
                # 多跳追溯：如果证据来自 Dataset
                elif ev_type == "dataset":
                    ds = get_dataset(ev_id)
                    if ds:
                        ancestors.append({"id": project_id, "type": "project", "title": "Dataset from Project"})

            # 后置影响：Next Action / NextExperiment
            descendants.append({"id": "next_action", "type": "next_experiment", "title": c.get("next_action", "Next Research Action")})

    elif node_id.startswith("art_"):
        node_type = "artifact"
        art = get_artifact(node_id)
        if art:
            if art.get("source_record_id"):
                ancestors.append({"id": art["source_record_id"], "type": "run", "title": "Producer Run"})
            # 查找哪些结论引用了该 Artifact
            concs = list_conclusions(project_id)
            for c in concs:
                if any(ref.get("id") == node_id for ref in c.get("evidence_refs", [])):
                    descendants.append({"id": c["id"], "type": "conclusion", "title": c.get("text", "")[:40]})

    elif node_id.startswith("run_"):
        node_type = "run"
        r = get_run(node_id)
        if r:
            if r.get("experiment_id"):
                ancestors.append({"id": r["experiment_id"], "type": "experiment", "title": "Experiment Protocol"})
            descendants.append({"id": "analysis", "type": "analysis", "title": "Data Analysis & EDA"})
            # 查找产生的 Artifacts
            for a in list_artifacts(project_id):
                if a.get("source_record_id") == node_id:
                    descendants.append({"id": a["id"], "type": "artifact", "title": a.get("name", "")})

    elif node_id.startswith("hyp_"):
        node_type = "hypothesis"
        h = get_hypothesis(node_id)
        if h:
            ancestors.append({"id": "project_rq", "type": "question", "title": "Core Research Question"})
            for eid in h.get("experiment_ids", []):
                descendants.append({"id": eid, "type": "experiment", "title": "Test Experiment"})
            # 查找直接支持该假说的结论
            for c in list_conclusions(project_id):
                if c.get("hypothesis_id") == node_id:
                    descendants.append({"id": c["id"], "type": "conclusion", "title": c.get("text", "")[:40]})

    elif node_id.startswith("ds_"):
        node_type = "dataset"
        ancestors.append({"id": project_id, "type": "project", "title": "Project Dataset Store"})
        descendants.append({"id": "duckdb_analytics", "type": "analysis", "title": "DuckDB Analytics"})

    elif node_id.startswith("paper_") or node_id.startswith("W") or node_id.startswith("arxiv_") or node_id.startswith("s2_"):
        node_type = "paper"
        ancestors.append({"id": project_id, "type": "project", "title": "Literature Ingestion"})
        # 查找引用该论文的结论
        for c in list_conclusions(project_id):
            if any(ref.get("id") == node_id for ref in c.get("evidence_refs", [])):
                descendants.append({"id": c["id"], "type": "conclusion", "title": c.get("text", "")[:40]})

    # 去重
    seen_a = set()
    dedup_ancestors = []
    for a in ancestors:
        if a["id"] not in seen_a:
            seen_a.add(a["id"])
            dedup_ancestors.append(a)

    seen_d = set()
    dedup_descendants = []
    for d in descendants:
        if d["id"] not in seen_d:
            seen_d.add(d["id"])
            dedup_descendants.append(d)

    return {
        "node_id": node_id,
        "node_type": node_type,
        "ancestors": dedup_ancestors,
        "descendants": dedup_descendants,
    }


@app.get("/api/projects/{project_id}/timeline")
def get_project_timeline_route(project_id: str):
    """获取 Project 的真实科研演进时间线"""
    from backend.domain.timeline import get_project_timeline
    events = get_project_timeline(project_id)
    return {"project_id": project_id, "events": events, "total": len(events)}


@app.post("/api/projects/{project_id}/memory/ask")
def ask_project_research_memory(project_id: str, body: dict):
    """基于科研认知记忆 2.0 与证据天平回答用户提问（无 CoT 暴露，防认知固化）"""
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")
    from backend.domain.memory import query_research_memory
    res = query_research_memory(
        project_id=project_id,
        question=question,
        include_contradictions=body.get("include_contradictions", True),
        include_failed_experiments=body.get("include_failed_experiments", True),
        include_alternatives=body.get("include_alternatives", True),
        include_unexplored=body.get("include_unexplored", True),
    )
    return res


@app.get("/api/projects/{project_id}/memory/balance")
def get_project_evidence_balance_route(project_id: str, hypothesis_id: Optional[str] = None):
    """获取课题或指定假说的证据天平 (Supporting vs Contradicting vs Unknown)"""
    from backend.domain.memory import build_evidence_balance
    return build_evidence_balance(project_id=project_id, hypothesis_id=hypothesis_id)


@app.get("/api/projects/{project_id}/memory/unexplored")
def get_project_unexplored_space_route(project_id: str):
    """获取课题超参数与物理维度的未探索盲区 (Unexplored Space)"""
    from backend.domain.memory import discover_unexplored_space
    unexplored = discover_unexplored_space(project_id=project_id)
    return {"project_id": project_id, "unexplored_space": unexplored, "total": len(unexplored)}


@app.get("/api/projects/{project_id}/memory/alternatives")
def get_project_alternative_hypotheses_route(project_id: str, hypothesis_id: Optional[str] = None):
    """获取针对当前观测指标的竞争性机制假说 (Alternative Hypotheses / AI Suggestions)"""
    from backend.domain.memory import generate_alternative_hypotheses
    alternatives = generate_alternative_hypotheses(project_id=project_id, hypothesis_id=hypothesis_id)
    return {"project_id": project_id, "alternative_hypotheses": alternatives, "total": len(alternatives)}


# =============================================================================
# V2.5 API — Active Exploration Engine & Epistemic Pruning (Phase 18)
# =============================================================================

@app.get("/api/projects/{project_id}/exploration/candidates")
def get_exploration_candidates_route(project_id: str, max_candidates: int = 4):
    """获取主动科学探索引擎生成的多范式候选实验组合 (Type A, B, C, D)"""
    from backend.domain.exploration import generate_candidate_experiments
    return generate_candidate_experiments(project_id=project_id, max_candidates=max_candidates)


@app.get("/api/projects/{project_id}/exploration/discrimination")
def get_hypothesis_discrimination_route(project_id: str):
    """获取竞争性假说区分度矩阵 (Hypothesis Discrimination Matrix)"""
    from backend.domain.exploration import build_hypothesis_discrimination_matrix
    return build_hypothesis_discrimination_matrix(project_id=project_id)


@app.get("/api/projects/{project_id}/exploration/pruning")
def get_epistemic_pruning_advisory_route(project_id: str):
    """获取假说认知修剪与资源优化顾问建议 (非破坏性，不自动物理删除)"""
    from backend.domain.exploration import analyze_epistemic_pruning
    return analyze_epistemic_pruning(project_id=project_id)


class ApproveCandidateRequest(BaseModel):
    candidate_id: str
    candidate_data: Optional[Dict[str, Any]] = None


@app.post("/api/projects/{project_id}/exploration/approve")
def approve_candidate_experiment_route(project_id: str, body: ApproveCandidateRequest):
    """科研人员确认批准候选实验，生成正式实验草稿并绑定血缘"""
    _assert_writable()
    from backend.domain.exploration import approve_candidate_experiment
    try:
        res = approve_candidate_experiment(
            project_id=project_id,
            candidate_id=body.candidate_id,
            candidate_data=body.candidate_data,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# V2.6 API — Product Hardening (Diary, Session, Run Comparison)
# =============================================================================

@app.get("/api/projects/{project_id}/diary")
def get_project_diary_route(project_id: str):
    """获取课题下的科研日记与反思列表"""
    from backend.domain.diary import list_diary_entries
    entries = list_diary_entries(project_id)
    return {"project_id": project_id, "entries": entries, "total": len(entries)}


class CreateDiaryRequest(BaseModel):
    title: str
    content: str
    entry_date: Optional[str] = None
    tags: Optional[List[str]] = None
    linked_hypothesis_id: Optional[str] = None
    linked_experiment_id: Optional[str] = None


@app.post("/api/projects/{project_id}/diary")
def create_project_diary_route(project_id: str, body: CreateDiaryRequest):
    """记录科研人员每日思考与主观观察 (USER_BELIEF / OBSERVATION)"""
    _assert_writable()
    from backend.domain.diary import create_diary_entry
    entry = create_diary_entry(
        project_id=project_id,
        title=body.title,
        content=body.content,
        entry_date=body.entry_date,
        tags=body.tags,
        linked_hypothesis_id=body.linked_hypothesis_id,
        linked_experiment_id=body.linked_experiment_id,
    )
    return {"success": True, "entry": entry}


@app.delete("/api/projects/{project_id}/diary/{entry_id}")
def delete_project_diary_route(project_id: str, entry_id: str):
    """删除指定的科研日记条目"""
    _assert_writable()
    from backend.domain.diary import delete_diary_entry
    ok = delete_diary_entry(project_id, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Diary entry not found")
    return {"success": True, "deleted_id": entry_id}


@app.get("/api/projects/{project_id}/sessions")
def get_project_sessions_route(project_id: str):
    """获取课题下的科研工作会话记录"""
    from backend.domain.session import list_research_sessions
    sessions = list_research_sessions(project_id)
    return {"project_id": project_id, "sessions": sessions, "total": len(sessions)}


class CreateSessionRequest(BaseModel):
    title: str
    goal: Optional[str] = ""
    actions_summary: Optional[List[str]] = None
    visited_papers: Optional[List[str]] = None
    executed_runs: Optional[List[str]] = None
    updated_hypotheses: Optional[List[str]] = None
    reached_conclusions: Optional[List[str]] = None
    next_step: Optional[str] = ""


@app.post("/api/projects/{project_id}/sessions")
def create_project_session_route(project_id: str, body: CreateSessionRequest):
    """记录一轮科研工作会话 (Research Session)"""
    _assert_writable()
    from backend.domain.session import create_research_session
    sess = create_research_session(
        project_id=project_id,
        title=body.title,
        goal=body.goal or "",
        actions_summary=body.actions_summary,
        visited_papers=body.visited_papers,
        executed_runs=body.executed_runs,
        updated_hypotheses=body.updated_hypotheses,
        reached_conclusions=body.reached_conclusions,
        next_step=body.next_step or "",
    )
    return {"success": True, "session": sess}


class CompareRunsRequest(BaseModel):
    run_ids: List[str]


@app.post("/api/runs/compare")
def compare_runs_route(body: CompareRunsRequest):
    """横向多 Run 参数、指标与产物对比矩阵"""
    from backend.domain.run import compare_runs
    return compare_runs(body.run_ids)




# =============================================================================
# Open Research Stack APIs — Literature (OpenAlex, arXiv, S2)
# =============================================================================

@app.get("/api/literature/search")
def search_literature_route(query: str, source: str = "openalex", limit: int = 8):
    """跨数据源学术文献检索 (OpenAlex / arXiv / Semantic Scholar)"""
    from backend.integrations.literature import search_literature
    papers = search_literature(query=query, source=source, limit=limit)
    return {"query": query, "source": source, "papers": papers, "count": len(papers)}


@app.get("/api/literature/paper/{paper_id}")
def get_literature_paper_route(paper_id: str, source: str = "openalex"):
    """获取单篇文献完整学术元数据"""
    from backend.integrations.literature import get_literature_paper
    paper = get_literature_paper(paper_id=paper_id, source=source)
    if not paper:
        raise HTTPException(status_code=404, detail="未检索到该文献")
    return {"paper": paper}


@app.post("/api/projects/{project_id}/papers")
def save_project_paper_route(project_id: str, body: dict):
    """将检索到的文献实体保存沉淀至 Project 课题下"""
    from backend.domain.paper import save_paper_to_project
    paper_data = body.get("paper", body)
    hyp_id = body.get("linked_hypothesis_id")
    q_text = body.get("linked_question")
    try:
        saved = save_paper_to_project(
            project_id=project_id,
            paper_data=paper_data,
            linked_hypothesis_id=hyp_id,
            linked_question=q_text,
        )
        return {"ok": True, "paper": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}/papers")
def list_project_papers_route(project_id: str):
    """获取 Project 下保存的所有文献"""
    from backend.domain.paper import list_project_papers
    papers = list_project_papers(project_id)
    return {"project_id": project_id, "papers": papers, "total": len(papers)}


@app.post("/api/projects/{project_id}/papers/import-direct")
def import_direct_paper_route(project_id: str, body: dict):
    """直接导入 BibTeX 文本代码或 DOI，免爬虫秒级入库"""
    from backend.domain.paper import save_paper_to_project
    from backend.integrations.literature.bibtex_parser import parse_bibtex
    from backend.integrations.literature.crossref import CrossRefProvider
    
    raw_text = (body.get("raw_text") or "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="请输入 BibTeX 文本或 DOI")

    saved_list = []
    # 1. 尝试作为 BibTeX 解析
    if "@" in raw_text and "{" in raw_text:
        parsed_papers = parse_bibtex(raw_text)
        for p in parsed_papers:
            saved = save_paper_to_project(project_id, p.to_dict())
            saved_list.append(saved)
    else:
        # 2. 尝试作为 DOI 或 DOI 列表解析
        doi_candidates = [d.strip() for d in raw_text.replace("\n", ",").split(",") if d.strip()]
        cr = CrossRefProvider()
        for cand in doi_candidates:
            clean_doi = cand.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            p = cr.get_paper(clean_doi)
            if p:
                saved = save_paper_to_project(project_id, p.to_dict())
                saved_list.append(saved)
            else:
                # 兜底构造 DOI 实体
                fallback_paper = {
                    "paper_id": f"doi:{clean_doi}",
                    "title": f"DOI: {clean_doi}",
                    "authors": [],
                    "abstract": f"Directly imported DOI {clean_doi}",
                    "doi": clean_doi,
                    "url": f"https://doi.org/{clean_doi}",
                    "source": "doi_import",
                }
                saved = save_paper_to_project(project_id, fallback_paper)
                saved_list.append(saved)

    return {"ok": True, "saved_count": len(saved_list), "papers": saved_list}


@app.delete("/api/projects/{project_id}/papers/{paper_id}")
def delete_project_paper_route(project_id: str, paper_id: str):
    """从 Project 移除文献"""
    from backend.domain.paper import delete_paper_from_project
    ok = delete_paper_from_project(project_id, paper_id)
    return {"ok": ok}


@app.post("/api/projects/{project_id}/papers/upload")
def upload_project_paper_route(project_id: str, body: dict):
    """上传本地 PDF/TXT/MD 论文并提取全文内容"""
    import base64
    from backend.domain.paper import save_paper_to_project
    from backend.domain.paper_reader import extract_text_from_file

    filename = body.get("filename", "uploaded_paper.pdf")
    content_b64 = body.get("content_base64", "")
    raw_text = body.get("text", "")

    if content_b64:
        file_bytes = base64.b64decode(content_b64)
        extracted_text, meta = extract_text_from_file(file_bytes, filename)
    elif raw_text:
        extracted_text = raw_text
        meta = {"filename": filename, "page_count": 1}
    else:
        raise HTTPException(status_code=400, detail="未提供文件内容")

    paper_id = f"local_{uuid.uuid4().hex[:10]}"
    title = meta.get("pdf_title") or Path(filename).stem.replace("_", " ").title()
    authors = [meta.get("pdf_author")] if meta.get("pdf_author") else ["Local Upload"]

    paper_data = {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "abstract": extracted_text[:1200] if len(extracted_text) > 1200 else extracted_text,
        "full_text": extracted_text,
        "url": "",
        "source": "local_upload",
        "metadata": meta,
    }
    saved = save_paper_to_project(project_id, paper_data)
    return {"ok": True, "paper": saved}


@app.post("/api/projects/{project_id}/papers/{paper_id}/analyze")
def analyze_project_paper_route(project_id: str, paper_id: str, body: dict = None):
    """触发 AI 自动化深度研读与假说提炼"""
    from backend.domain.paper import get_paper, update_project_paper
    from backend.domain.paper_reader import read_and_analyze_paper

    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    text_to_analyze = paper.get("full_text") or paper.get("abstract") or paper.get("title", "")
    res = read_and_analyze_paper(
        paper_text=text_to_analyze,
        title=paper.get("title", ""),
        authors=paper.get("authors", []),
    )

    if res.get("success"):
        # 更新文献实体中的研读报告
        update_project_paper(project_id, paper_id, {"reading_analysis": res["analysis"]})

    return res


@app.post("/api/projects/{project_id}/papers/{paper_id}/adopt-hypothesis")
def adopt_paper_hypothesis_route(project_id: str, paper_id: str, body: dict = None):
    """将文献研读提炼出的候选假说一键转化为课题假说"""
    from backend.domain.hypothesis import create_hypothesis

    hyp = (body or {}).get("hypothesis", body or {})
    title = hyp.get("title") or "从文献提炼的假说"
    desc = hyp.get("statement") or hyp.get("description") or ""
    rationale = hyp.get("rationale", "")
    suggested_exp = hyp.get("suggested_experiment", "")

    full_desc = f"{desc}\n\n依据: {rationale}\n建议实验: {suggested_exp}"
    created = create_hypothesis(
        project_id=project_id,
        title=title,
        description=full_desc,
        source_paper_id=paper_id,
    )
    return {"ok": True, "hypothesis": created}


# =============================================================================
# Open Research Stack APIs — Data & DuckDB
# =============================================================================

@app.post("/api/projects/{project_id}/datasets")
def create_dataset_route(project_id: str, body: dict):
    """创建结构化 Dataset (CSV/Parquet)"""
    from backend.domain.dataset import create_dataset_from_csv
    name = body.get("name", "New Dataset")
    csv_content = body.get("csv_content", "")
    metadata = body.get("metadata", {})
    try:
        ds = create_dataset_from_csv(project_id=project_id, name=name, csv_content=csv_content, metadata=metadata)
        return {"ok": True, "dataset": ds}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}/datasets")
def list_project_datasets_route(project_id: str):
    """获取 Project 下的所有 Dataset"""
    from backend.domain.dataset import list_project_datasets
    datasets = list_project_datasets(project_id)
    return {"project_id": project_id, "datasets": datasets, "total": len(datasets)}


@app.get("/api/datasets/{dataset_id}")
def get_dataset_route(dataset_id: str):
    """获取单个 Dataset 详情"""
    from backend.domain.dataset import get_dataset
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset 不存在")
    return {"dataset": ds}


@app.post("/api/datasets/{dataset_id}/query")
def query_dataset_sql_route(dataset_id: str, body: dict):
    """通过 DuckDB 执行本地 SQL 分析查询"""
    from backend.domain.dataset import query_dataset_sql
    sql = body.get("sql", "SELECT * FROM dataset LIMIT 20")
    limit = body.get("limit", 50)
    res = query_dataset_sql(dataset_id=dataset_id, sql=sql, limit=limit)
    return res


@app.get("/api/datasets/{dataset_id}/summary")
def get_dataset_summary_route(dataset_id: str):
    """获取 Dataset 统计概览"""
    from backend.domain.dataset import get_dataset_summary
    res = get_dataset_summary(dataset_id)
    return res


@app.get("/api/datasets/search")
def search_online_datasets_route(query: str, source: str = "huggingface", limit: int = 10):
    """跨平台公开数据集检索 (Hugging Face / Papers With Code)"""
    from backend.integrations.datasets import search_online_datasets
    datasets = search_online_datasets(query=query, source=source, limit=limit)
    return {"query": query, "source": source, "datasets": datasets, "count": len(datasets)}


@app.post("/api/projects/{project_id}/datasets/import-online")
def import_online_dataset_route(project_id: str, body: dict):
    """将在线检索到的公开数据集沉淀至课题项目"""
    from backend.domain.dataset import save_online_dataset_to_project
    dataset_data = body.get("dataset", body)
    try:
        saved = save_online_dataset_to_project(project_id=project_id, dataset_data=dataset_data)
        return {"ok": True, "dataset": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset_route(dataset_id: str):
    """删除 Dataset"""
    from backend.domain.dataset import delete_dataset
    ok = delete_dataset(dataset_id)
    return {"ok": ok}


# =============================================================================
# Open Research Stack APIs — Notebook & MLflow
# =============================================================================

@app.post("/api/projects/{project_id}/notebooks/import")
def import_notebook_route(project_id: str, body: dict):
    """解析并导入 Jupyter Notebook 为 Artifact"""
    from backend.integrations.notebook.jupyter import notebook_adapter
    name = body.get("name", "Untitled Notebook")
    ipynb_str = body.get("ipynb_str", "{}")
    rec_id = body.get("source_record_id")
    try:
        art = notebook_adapter.import_notebook_as_artifact(
            project_id=project_id,
            name=name,
            ipynb_str=ipynb_str,
            source_record_id=rec_id,
        )
        return {"ok": True, "artifact": art}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/integrations/mlflow/sync")
def sync_mlflow_runs_route(body: dict):
    """同步本地 MLflow 实验 Runs 到 ResearchOS Experiment"""
    from backend.integrations.experiment.mlflow import mlflow_adapter
    mlflow_exp_dir = body.get("mlflow_exp_dir", "")
    target_exp_id = body.get("target_experiment_id", "")
    if not mlflow_exp_dir or not target_exp_id:
        raise HTTPException(status_code=400, detail="mlflow_exp_dir 与 target_experiment_id 不能为空")
    res = mlflow_adapter.sync_runs_to_experiment(mlflow_exp_dir, target_exp_id)
    return res


# =============================================================================
# V2 API — Research Graph V2
# =============================================================================

@app.get("/api/projects/{project_id}/graph")
def get_project_research_graph(project_id: str):
    """获取 Project 的 Research Graph V2（含 Hypothesis、Paper、Project 节点）"""
    from backend.domain.project import get_project as _get_project
    from backend.domain.hypothesis import list_hypotheses as _list_hyps
    from src.graph.builder import build_graph_from_record, build_research_graph

    project = _get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project 不存在")

    hypotheses = _list_hyps(project_id=project_id)

    # 合并 project 下所有实验的图谱
    records_dir = DATA_DIR / "records"
    base_graph: dict = {"entities": [], "relations": []}

    for exp_id in project.get("experiment_ids", []):
        candidates = list(records_dir.glob(f"*{exp_id}*.json")) if records_dir.exists() else []
        for c in candidates:
            try:
                record = json.loads(c.read_text(encoding="utf-8"))
                sub_graph = build_graph_from_record(record)
                base_graph["entities"].extend(sub_graph.get("entities", []))
                base_graph["relations"].extend(sub_graph.get("relations", []))
            except Exception:
                pass

    # 叠加 V2 层与 Runs/Artifacts/Conclusions/Papers 实体
    from backend.domain.run import list_runs
    from backend.domain.artifact import list_artifacts
    from backend.domain.conclusion import list_conclusions
    from backend.domain.paper import list_project_papers

    proj_runs = list_runs()
    proj_artifacts = list_artifacts(project_id)
    proj_conclusions = list_conclusions(project_id)
    proj_papers = list_project_papers(project_id)

    research_graph = build_research_graph(
        base_graph=base_graph,
        project=project,
        hypotheses=hypotheses,
        runs=proj_runs,
        artifacts=proj_artifacts,
        conclusions=proj_conclusions,
        papers=proj_papers,
    )
    return research_graph


# ═══════════════════════════════════════════════════════════════
# Phase 6：Data Agent API
# ═══════════════════════════════════════════════════════════════

class RunPythonRequest(BaseModel):
    code: str
    timeout: int = 10
    context: dict = {}

class RunEDARequest(BaseModel):
    record_id: str

class SensitivityRequest(BaseModel):
    record_ids: list
    target_metric: str = "accuracy"

class GenerateChartRequest(BaseModel):
    data: list
    chart_type: str = "bar"
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""


@app.post("/api/data/python")
async def run_python(body: RunPythonRequest):
    _assert_writable()
    from backend.agent.tools.registry import registry
    return registry.call("run_python", caller="api", code=body.code, timeout=body.timeout)


@app.post("/api/data/eda")
async def run_eda(body: RunEDARequest):
    from backend.agent.tools.registry import registry
    return registry.call("run_eda", caller="api", record_id=body.record_id)


@app.post("/api/projects/{project_id}/analyze/sensitivity")
async def run_sensitivity(project_id: str, body: SensitivityRequest):
    from backend.domain.data_agent import analyze_params_sensitivity
    return analyze_params_sensitivity(body.record_ids, body.target_metric)


@app.post("/api/data/chart")
async def gen_chart(body: GenerateChartRequest):
    _assert_writable()
    from backend.domain.data_agent import generate_chart
    return generate_chart(body.data, body.chart_type, body.title, body.xlabel, body.ylabel)


# ═══════════════════════════════════════════════════════════════
# Phase 7：Artifact API
# ═══════════════════════════════════════════════════════════════

class CreateArtifactRequest(BaseModel):
    project_id: str
    name: str
    type: str
    content: str
    source_record_id: str = None
    metadata: dict = {}
    content_encoding: str = "text"
    mime_type: str = None


@app.post("/api/artifacts")
async def create_artifact(body: CreateArtifactRequest):
    _assert_writable()
    from backend.domain.artifact import create_artifact as _create
    return _create(
        project_id=body.project_id,
        name=body.name,
        artifact_type=body.type,
        content=body.content,
        source_record_id=body.source_record_id,
        metadata=body.metadata,
        content_encoding=body.content_encoding,
        mime_type=body.mime_type,
    )


@app.get("/api/projects/{project_id}/artifacts")
async def list_project_artifacts(project_id: str, type: str = None):
    from backend.domain.artifact import list_artifacts
    return {"artifacts": list_artifacts(project_id, type_filter=type)}


@app.get("/api/artifacts/{artifact_id}")
async def get_artifact_detail(artifact_id: str, project_id: str = None):
    from backend.domain.artifact import get_artifact
    art = get_artifact(artifact_id, project_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artifact 不存在")
    return art


@app.get("/api/artifacts/{artifact_id}/content")
async def get_artifact_content_route(artifact_id: str):
    import base64
    from fastapi.responses import Response
    from backend.domain.artifact import get_artifact
    art = get_artifact(artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artifact 不存在")

    content = art.get("content", "")
    mime_type = art.get("mime_type", "text/plain")

    if art.get("content_encoding") == "base64" or art.get("type") == "chart":
        try:
            raw_bytes = base64.b64decode(content)
            return Response(content=raw_bytes, media_type=mime_type)
        except Exception:
            return Response(content=content.encode("utf-8"), media_type="text/plain")

    return Response(content=content.encode("utf-8"), media_type=mime_type)


@app.get("/api/artifacts/{artifact_id}/lineage")
async def get_lineage(artifact_id: str):
    from backend.domain.artifact import get_artifact_lineage
    return get_artifact_lineage(artifact_id)


@app.delete("/api/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, project_id: str = None):
    _assert_writable()
    from backend.domain.artifact import delete_artifact as _delete
    ok = _delete(artifact_id, project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Artifact 不存在")
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════
# Phase 8：Conclusion & Evidence Reverse-Lookup API
# ═══════════════════════════════════════════════════════════════

class CreateConclusionRequest(BaseModel):
    text: str
    hypothesis_id: str = None
    evidence_refs: list = []
    confidence: str = "medium"
    source: str = "user"


class AddEvidenceRequest(BaseModel):
    type: str
    id: str
    snippet: str = ""


class UpdateConclusionRequest(BaseModel):
    text: str = None
    confidence: str = None
    hypothesis_id: str = None


@app.post("/api/projects/{project_id}/conclusions")
async def create_conclusion_route(project_id: str, body: CreateConclusionRequest):
    _assert_writable()
    from backend.domain.conclusion import create_conclusion
    return create_conclusion(
        project_id=project_id,
        text=body.text,
        hypothesis_id=body.hypothesis_id,
        evidence_refs=body.evidence_refs,
        confidence=body.confidence,
        source=body.source,
    )


@app.get("/api/projects/{project_id}/conclusions")
async def list_conclusions_route(project_id: str):
    from backend.domain.conclusion import list_conclusions
    return {"conclusions": list_conclusions(project_id)}


@app.get("/api/conclusions/{conclusion_id}")
async def get_conclusion_route(conclusion_id: str):
    from backend.domain.conclusion import get_conclusion
    c = get_conclusion(conclusion_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Conclusion 不存在")
    return c


@app.put("/api/conclusions/{conclusion_id}")
async def update_conclusion_route(conclusion_id: str, body: UpdateConclusionRequest):
    _assert_writable()
    from backend.domain.conclusion import update_conclusion
    c = update_conclusion(conclusion_id, text=body.text, confidence=body.confidence, hypothesis_id=body.hypothesis_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Conclusion 不存在")
    return c


@app.post("/api/conclusions/{conclusion_id}/evidence")
async def add_evidence_route(conclusion_id: str, body: AddEvidenceRequest):
    _assert_writable()
    from backend.domain.conclusion import add_evidence_to_conclusion
    c = add_evidence_to_conclusion(conclusion_id, body.type, body.id, body.snippet)
    if c is None:
        raise HTTPException(status_code=404, detail="Conclusion 不存在")
    return c


@app.delete("/api/conclusions/{conclusion_id}")
async def delete_conclusion_route(conclusion_id: str):
    _assert_writable()
    from backend.domain.conclusion import delete_conclusion
    ok = delete_conclusion(conclusion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conclusion 不存在")
    return {"ok": True}


@app.get("/api/evidence/{evidence_type}/{evidence_id}/conclusions")
async def get_conclusions_for_evidence(evidence_type: str, evidence_id: str):
    """反向追溯：查询支持了哪些 Conclusion"""
    from backend.domain.conclusion import get_conclusions_by_evidence
    return {"conclusions": get_conclusions_by_evidence(evidence_type, evidence_id)}


@app.get("/api/experiments/{experiment_id}/conclusions")
async def get_experiment_conclusions(experiment_id: str):
    """查询引用了该实验作为证据的所有科研结论"""
    from backend.domain.conclusion import get_conclusions_by_evidence
    return {"conclusions": get_conclusions_by_evidence("experiment", experiment_id)}


# ═══════════════════════════════════════════════════════════════
# Phase 9 & P0: ExperimentRun & HITL Approval API
# ═══════════════════════════════════════════════════════════════

class CreateRunRequest(BaseModel):
    actual_parameters: dict = {}
    dataset: str = ""
    metrics: dict = {}
    logs: list = []
    artifacts: list = []
    status: str = "pending"
    execution_origin: str = "LOCAL_SANDBOX"
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    repository: Optional[str] = None
    ai_tool_used: Optional[str] = None
    ai_task_description: Optional[str] = None


class UpdateRunRequest(BaseModel):
    status: str = None
    actual_parameters: dict = None
    dataset: str = None
    metrics: dict = None
    logs: list = None
    artifacts: list = None
    error: str = None


class ExecuteRunRequest(BaseModel):
    execution_code: str = None
    approval_id: str = None
    timeout: int = 30


@app.get("/api/experiments/{experiment_id}/runs")
async def get_experiment_runs(experiment_id: str):
    from backend.domain.run import get_experiment_with_runs
    return get_experiment_with_runs(experiment_id)


@app.post("/api/experiments/{experiment_id}/runs")
async def create_experiment_run_route(experiment_id: str, body: CreateRunRequest):
    _assert_writable()
    from backend.domain.run import create_run
    return create_run(
        experiment_id=experiment_id,
        actual_parameters=body.actual_parameters,
        dataset=body.dataset,
        metrics=body.metrics,
        logs=body.logs,
        artifacts=body.artifacts,
        status=body.status,
        execution_origin=body.execution_origin,
        git_commit=body.git_commit,
        git_branch=body.git_branch,
        repository=body.repository,
        ai_tool_used=body.ai_tool_used,
        ai_task_description=body.ai_task_description,
    )


class QuickCaptureRequest(BaseModel):
    title: str
    what_i_did: str
    tools_used: Optional[List[str]] = None
    what_happened: str
    what_surprised_me: Optional[str] = ""
    current_belief: Optional[str] = ""
    next_step: Optional[str] = ""
    ai_tool_used: Optional[str] = "None"
    git_commit: Optional[str] = None
    linked_hypothesis_id: Optional[str] = None
    linked_experiment_id: Optional[str] = None


@app.post("/api/projects/{project_id}/quick-capture")
def quick_capture_route(project_id: str, body: QuickCaptureRequest):
    """科研人员轻量快速记录实验与手记 (Quick Capture)"""
    _assert_writable()
    from backend.domain.session import create_research_session
    sess = create_research_session(
        project_id=project_id,
        title=body.title,
        goal=body.what_i_did,
        what_i_did=body.what_i_did,
        tools_used=body.tools_used,
        what_happened=body.what_happened,
        what_surprised_me=body.what_surprised_me or "",
        current_belief=body.current_belief or "",
        next_step=body.next_step or "",
        ai_tool_used=body.ai_tool_used or "None",
        git_commit=body.git_commit,
        updated_hypotheses=[body.linked_hypothesis_id] if body.linked_hypothesis_id else [],
    )
    return {"success": True, "session": sess}


@app.get("/api/projects/{project_id}/external-prompt")
def get_external_prompt_route(project_id: str, hypothesis_id: Optional[str] = None):
    """一键生成供外部 Codex / Claude Code / ChatGPT 使用的结构化上下文 Prompt"""
    from backend.domain.session import generate_external_prompt
    return generate_external_prompt(project_id, hypothesis_id)


@app.get("/api/runs/{run_id}")
async def get_run_route(run_id: str):
    from backend.domain.run import get_run
    r = get_run(run_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return r


@app.put("/api/runs/{run_id}")
async def update_run_route(run_id: str, body: UpdateRunRequest):
    _assert_writable()
    from backend.domain.run import update_run
    r = update_run(
        run_id,
        status=body.status,
        actual_parameters=body.actual_parameters,
        dataset=body.dataset,
        metrics=body.metrics,
        logs=body.logs,
        artifacts=body.artifacts,
        error=body.error,
    )
    if r is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return r


@app.delete("/api/runs/{run_id}")
async def delete_run_route(run_id: str):
    _assert_writable()
    from backend.domain.run import delete_run
    ok = delete_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return {"ok": True}


@app.post("/api/runs/{run_id}/execute")
async def execute_run_route(run_id: str, body: ExecuteRunRequest):
    """
    执行 Run 实例 — 必须通过 ToolRegistry 统一风控与审批阻断
    """
    _assert_writable()
    from backend.agent.tools.registry import registry
    res = registry.call(
        "execute_run",
        caller="webui_api",
        approval_id=body.approval_id,
        run_id=run_id,
        execution_code=body.execution_code,
        timeout=body.timeout,
    )
    return res


# ─── V2.4 Deep Research APIs (PDF, Multi-Dataset Analysis & Experiment Coder) ─────

class UploadPdfRequest(BaseModel):
    pdf_base64: str | None = None
    filename: str = "source.pdf"

@app.post("/api/projects/{project_id}/papers/{paper_id}/pdf")
async def upload_paper_pdf_route(project_id: str, paper_id: str, body: UploadPdfRequest):
    """上传并解析文献 PDF 全文"""
    _assert_writable()
    import base64
    from backend.domain.paper import save_paper_pdf
    
    if not body.pdf_base64:
        raise HTTPException(status_code=400, detail="缺少 PDF base64 数据")
    
    try:
        pdf_bytes = base64.b64decode(body.pdf_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base64 解码错误: {str(e)}")
    
    res = save_paper_pdf(project_id=project_id, paper_id=paper_id, pdf_bytes=pdf_bytes, filename=body.filename)
    return res


@app.get("/api/papers/{paper_id}/extracted")
async def get_paper_extracted_route(paper_id: str):
    """获取已解析的文献段落与页面结构"""
    from backend.domain.paper import get_paper_extracted_data
    data = get_paper_extracted_data(paper_id)
    if not data:
        raise HTTPException(status_code=404, detail="未找到该文献的 PDF 解析数据")
    return data


class CreatePdfEvidenceRequest(BaseModel):
    project_id: str
    page: int
    section: str = "General"
    paragraph_index: int = 0
    text: str
    claim: str | None = None
    hypothesis_id: str | None = None

@app.post("/api/papers/{paper_id}/evidence")
async def create_paper_evidence_route(paper_id: str, body: CreatePdfEvidenceRequest):
    """从 PDF 切片提取并沉淀 Evidence"""
    _assert_writable()
    from backend.domain.paper import create_paper_evidence_slice
    return create_paper_evidence_slice(
        project_id=body.project_id,
        paper_id=paper_id,
        page=body.page,
        section=body.section,
        paragraph_index=body.paragraph_index,
        text=body.text,
        claim=body.claim,
        hypothesis_id=body.hypothesis_id,
    )


class AskPaperRequest(BaseModel):
    question: str

@app.post("/api/papers/{paper_id}/ask")
async def ask_paper_route(paper_id: str, body: AskPaperRequest):
    """对文献全文执行深度问答并提供精准章节定位"""
    from backend.domain.paper import ask_paper_question
    return ask_paper_question(paper_id=paper_id, question=body.question)


class DatasetRelationshipsRequest(BaseModel):
    dataset_ids: list[str]

@app.post("/api/projects/{project_id}/datasets/relationships")
async def inspect_dataset_relationships_route(project_id: str, body: DatasetRelationshipsRequest):
    """多数据表 Schema 理解与自动 JOIN 关系探测"""
    from backend.domain.dataset import get_dataset
    from backend.integrations.data.relationship import relationship_inspector
    ds_list = [get_dataset(did) for did in body.dataset_ids if get_dataset(did)]
    return {
        "project_id": project_id,
        "relationships": relationship_inspector.discover_relationships(ds_list),
        "total": len(ds_list),
    }


class AnalysisPlanRequest(BaseModel):
    intent: str
    dataset_ids: list[str]
    target_metric: str | None = None
    group_col: str | None = None

@app.post("/api/projects/{project_id}/datasets/wizard/plan")
async def generate_analysis_plan_route(project_id: str, body: AnalysisPlanRequest):
    """根据分析意图生成统计分析向导方案"""
    from backend.integrations.data.wizard import analysis_wizard
    return analysis_wizard.generate_analysis_plan(
        intent=body.intent,
        dataset_ids=body.dataset_ids,
        target_metric=body.target_metric,
        group_col=body.group_col,
    )


class ExecuteAnalysisRequest(BaseModel):
    title: str
    dataset_id: str
    sql_query: str
    python_code: str | None = None
    source_record_id: str | None = None

@app.post("/api/projects/{project_id}/datasets/wizard/execute")
async def execute_analysis_route(project_id: str, body: ExecuteAnalysisRequest):
    """执行分析方案并将结果沉淀为 Analysis Artifact"""
    _assert_writable()
    from backend.integrations.data.wizard import analysis_wizard
    return analysis_wizard.execute_and_create_artifact(
        project_id=project_id,
        title=body.title,
        dataset_id=body.dataset_id,
        sql_query=body.sql_query,
        python_code=body.python_code,
        source_record_id=body.source_record_id,
    )


class GenerateCodeRequest(BaseModel):
    hypothesis_id: str | None = None
    dataset_id: str | None = None
    custom_instructions: str | None = None

@app.post("/api/projects/{project_id}/experiments/{experiment_id}/code/generate")
async def generate_experiment_code_route(project_id: str, experiment_id: str, body: GenerateCodeRequest):
    """生成实验 Python 脚本"""
    from backend.domain.experiment_coder import generate_experiment_code
    return generate_experiment_code(
        project_id=project_id,
        experiment_id=experiment_id,
        hypothesis_id=body.hypothesis_id,
        dataset_id=body.dataset_id,
        custom_instructions=body.custom_instructions,
    )


class RunCodeRequest(BaseModel):
    code: str
    timeout: int = 30

@app.post("/api/projects/{project_id}/experiments/{experiment_id}/code/run")
async def run_experiment_code_route(project_id: str, experiment_id: str, body: RunCodeRequest):
    """受控安全沙箱中执行实验脚本"""
    _assert_writable()
    from backend.domain.experiment_coder import execute_experiment_code_safely
    return execute_experiment_code_safely(
        project_id=project_id,
        experiment_id=experiment_id,
        code=body.code,
        timeout=body.timeout,
    )


class DebugCodeRequest(BaseModel):
    code: str
    error_traceback: str
    retry_count: int = 1

@app.post("/api/projects/{project_id}/experiments/{experiment_id}/code/debug")
async def debug_experiment_code_route(project_id: str, experiment_id: str, body: DebugCodeRequest):
    """针对实验报错进行根因分析与补丁修复"""
    _assert_writable()
    from backend.domain.experiment_coder import debug_experiment_code
    return debug_experiment_code(
        project_id=project_id,
        experiment_id=experiment_id,
        code=body.code,
        error_traceback=body.error_traceback,
        retry_count=body.retry_count,
    )


# ─── Approvals (HITL) API ──────────────────────────────────────

class ApprovalActionRequest(BaseModel):
    approver: str = "human_user"
    reason: str = ""


@app.get("/api/approvals/{approval_id}")
async def get_approval_route(approval_id: str):
    from backend.agent.security.guard import get_approval
    rec = get_approval(approval_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="审批工单不存在")
    return rec


@app.post("/api/approvals/{approval_id}/approve")
async def approve_route(approval_id: str, body: ApprovalActionRequest):
    _assert_writable()
    from backend.agent.security.guard import approve_request
    res = approve_request(approval_id, approver=body.approver)
    if res is None:
        raise HTTPException(status_code=404, detail="审批工单不存在")
    return res


@app.post("/api/approvals/{approval_id}/reject")
async def reject_route(approval_id: str, body: ApprovalActionRequest):
    _assert_writable()
    from backend.agent.security.guard import reject_request
    res = reject_request(approval_id, rejector=body.approver, reason=body.reason)
    if res is None:
        raise HTTPException(status_code=404, detail="审批工单不存在")
# =============================================================================
# V2.5 API — Local AI Gateway & Privacy Boundary (Phase 15)
# =============================================================================

@app.get("/api/llm/providers")
async def list_llm_providers_route():
    """获取所有可用大模型提供商清单与健康状态"""
    from backend.llm.gateway import llm_gateway
    return {
        "providers": llm_gateway.list_providers(),
        "active": llm_gateway.active_provider_name,
        "routing_policy": llm_gateway.routing_policy.value,
    }


@app.get("/api/llm/providers/{provider_id}/health")
async def get_llm_provider_health_route(provider_id: str):
    """检测指定 Provider 连通性与健康状态"""
    from backend.llm.gateway import llm_gateway
    prov = llm_gateway.get_provider(provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")
    return prov.health()


@app.get("/api/llm/providers/{provider_id}/models")
async def get_llm_provider_models_route(provider_id: str):
    """获取指定 Provider 上的可用模型列表"""
    from backend.llm.gateway import llm_gateway
    prov = llm_gateway.get_provider(provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")
    return {"provider": provider_id, "models": prov.list_models()}


class SelectProviderRequest(BaseModel):
    provider_name: str
    routing_policy: str | None = None


@app.post("/api/llm/providers/select")
async def select_llm_provider_route(body: SelectProviderRequest):
    """切换当前活跃大模型提供商与路由策略"""
    _assert_writable()
    from backend.llm.gateway import llm_gateway
    from backend.llm.base import RoutingPolicy
    try:
        llm_gateway.set_active_provider(body.provider_name)
        if body.routing_policy and body.routing_policy in RoutingPolicy._value2member_map_:
            llm_gateway.set_routing_policy(RoutingPolicy(body.routing_policy))
        return {
            "ok": True,
            "active_provider": llm_gateway.active_provider_name,
            "routing_policy": llm_gateway.routing_policy.value,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class LLMChatRequest(BaseModel):
    prompt: str
    project_id: str | None = None
    provider_name: str | None = None
    model: str | None = None
    temperature: float = 0.2
    approved_ticket_id: str | None = None


@app.post("/api/llm/chat")
async def llm_chat_route(body: LLMChatRequest):
    """通过 Privacy Gateway 安全路由大模型对话"""
    from backend.llm.gateway import llm_gateway
    from backend.security.privacy_gateway import PrivacyViolationError
    try:
        res = llm_gateway.safe_chat(
            messages=body.prompt,
            project_id=body.project_id,
            provider_name=body.provider_name,
            model=body.model,
            temperature=body.temperature,
            approved_ticket_id=body.approved_ticket_id,
        )
        return {
            "content": res.content,
            "model": res.model,
            "provider": res.provider_name,
            "finish_reason": res.finish_reason,
            "raw_response": res.raw_response,
        }
    except PrivacyViolationError as pve:
        raise HTTPException(
            status_code=403,
            detail={"error": "PRIVACY_DENIED", "message": str(pve), "blocked_items": pve.blocked_items},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PrivacyCheckRequest(BaseModel):
    text: str | None = None
    items: list[dict] | None = None
    project_id: str | None = None
    is_local_llm: bool = True


@app.post("/api/privacy/check")
async def privacy_check_route(body: PrivacyCheckRequest):
    """预先评估 Prompt 或 Context 的数据隐私分级与放行决策"""
    from backend.security.privacy_gateway import privacy_gateway
    if body.items:
        res = privacy_gateway.evaluate_context_items(
            items=body.items,
            is_local_llm=body.is_local_llm,
            project_id=body.project_id,
        )
    else:
        res = privacy_gateway.evaluate_text(
            text=body.text or "",
            is_local_llm=body.is_local_llm,
            project_id=body.project_id,
        )
    return {
        "allowed": res.allowed,
        "decision": res.decision.value,
        "classification": res.highest_classification.value,
        "reason": res.reason,
        "ticket_id": res.ticket_id,
        "blocked_items": res.blocked_items,
        "sensitive_items": res.sensitive_items,
    }


class PrivacyAuthorizeRequest(BaseModel):
    ticket_id: str
    action: str = "allow_once"


@app.post("/api/privacy/authorize")
async def privacy_authorize_route(body: PrivacyAuthorizeRequest):
    """用户显式授权或拒绝敏感上下文审批工单"""
    _assert_writable()
    from backend.security.privacy_gateway import privacy_gateway
    ok = privacy_gateway.authorize_ticket(body.ticket_id, action=body.action)
    return {"ok": ok, "ticket_id": body.ticket_id, "action": body.action}


@app.get("/api/privacy/audit")
async def privacy_audit_logs_route(limit: int = 50):
    """获取本地隐私合规与 AI 访问审计日志"""
    from backend.security.audit import get_privacy_audit_logs
    logs = get_privacy_audit_logs(limit=limit)
    return {"logs": logs, "total": len(logs)}


@app.get("/api/privacy/config")
async def privacy_config_route():
    """获取当前隐私路由策略与分级矩阵规则"""
    from backend.llm.gateway import llm_gateway
    return {
        "routing_policy": llm_gateway.routing_policy.value,
        "active_provider": llm_gateway.active_provider_name,
        "rules": {
            "PUBLIC": "ALLOW",
            "INTERNAL": "ALLOW (Local) / ASK (Cloud)",
            "SENSITIVE": "ASK (Requires Approval Ticket)",
            "RESTRICTED": "DENY (Hard Block)",
        },
    }


class UpdatePrivacyConfigRequest(BaseModel):
    routing_policy: str


@app.post("/api/privacy/config")
async def update_privacy_config_route(body: UpdatePrivacyConfigRequest):
    """更新全局 AI 隐私路由策略"""
    _assert_writable()
    from backend.llm.gateway import llm_gateway
    from backend.llm.base import RoutingPolicy
    if body.routing_policy in RoutingPolicy._value2member_map_:
        llm_gateway.set_routing_policy(RoutingPolicy(body.routing_policy))
        return {"ok": True, "routing_policy": llm_gateway.routing_policy.value}
    raise HTTPException(
        status_code=400,
        detail="Invalid routing policy. Choose from LOCAL_ONLY, LOCAL_PREFERRED, CLOUD_ALLOWED",
    )


# =============================================================================
# V2.5 API — Obsidian Knowledge Layer / Vault Bridge (Phase 16)
# =============================================================================

class VaultPreviewRequest(BaseModel):
    vault_path: str
    include: list[str] | None = None


@app.post("/api/projects/{project_id}/vault/preview")
async def preview_vault_export_route(project_id: str, body: VaultPreviewRequest):
    """预览项目导出至 Obsidian Vault 的文件清单与状态"""
    from pathlib import Path
    from backend.vault.exporter import preview_vault_export
    from backend.vault.models import VaultExportOptions
    opts = VaultExportOptions(include_entities=body.include) if body.include else VaultExportOptions()
    try:
        summary = preview_vault_export(project_id=project_id, vault_path=Path(body.vault_path), options=opts)
        return summary.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class VaultExportRequest(BaseModel):
    vault_path: str
    include: list[str] | None = None


@app.post("/api/projects/{project_id}/vault/export")
async def export_vault_route(project_id: str, body: VaultExportRequest):
    """执行项目全量实体导出至 Obsidian Vault 并生成 YAML + Wikilinks"""
    _assert_writable()
    from pathlib import Path
    from backend.vault.exporter import export_project_to_vault
    from backend.vault.models import VaultExportOptions
    opts = VaultExportOptions(include_entities=body.include) if body.include else VaultExportOptions()
    try:
        res = export_project_to_vault(project_id=project_id, vault_path=Path(body.vault_path), options=opts)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class VaultReconcileRequest(BaseModel):
    vault_path: str


@app.post("/api/projects/{project_id}/vault/reconcile")
async def reconcile_vault_route(project_id: str, body: VaultReconcileRequest):
    """检测 Obsidian Vault 中用户修改与文件状态"""
    from pathlib import Path
    from backend.vault.importer import reconcile_vault
    try:
        return reconcile_vault(vault_path=Path(body.vault_path), project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)
