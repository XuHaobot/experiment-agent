import json
import os
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse

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


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)
