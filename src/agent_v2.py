"""
AgentV2 — 基于 Function Calling 的智能实验助手。

替代原有的关键词路由 Agent (agent.py)，
让 LLM 自主决定调用哪个工具，支持多轮对话与工具链式调用。
"""

import json
import logging
from typing import Any

from src.llm_client import call_llm_with_tools, LLMClient
from src.storage import DATA_DIR
from src.tools.search_tool import search_records, hybrid_search
from src.tools.data_analysis_tool import analyze_data, evaluate_answer
from src.tools.report_tool import generate_markdown_report
from src.graph.query import search_graph


logger = logging.getLogger(__name__)

RECORDS_DIR = DATA_DIR / "records"


# ---------------------------------------------------------------------------
# Tool 定义 (OpenAI Function Calling 格式)
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_records",
            "description": (
                "搜索历史实验记录。支持按任务名、数据集、模型名、参数、错误信息等字段进行"
                "关键词和语义混合检索。返回匹配的实验记录列表。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或自然语言查询",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量上限，默认5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_graph",
            "description": (
                "在知识图谱中搜索相关实体和关系。知识图谱包含实验中涉及的模型、"
                "数据集、参数、错误、解决方案等实体及其关联。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": (
                "对实验数据进行分析。支持三种分析类型：\n"
                "- param_compare: 对比多条记录的参数差异\n"
                "- trend: 按时间排列分析指标变化趋势\n"
                "- summary: 对指定记录做综合摘要"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "record_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要分析的实验记录 ID 列表",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["param_compare", "trend", "summary"],
                        "description": "分析类型，默认 summary",
                        "default": "summary",
                    },
                },
                "required": ["record_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "根据实验记录 ID 生成 Markdown 格式的复盘报告，包含任务概述、参数分析、错误诊断和结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "实验记录 ID",
                    },
                },
                "required": ["record_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_records",
            "description": "列出所有历史实验记录的摘要信息（ID、任务、模型、数据集、创建时间），用于了解有哪些可用数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数量上限，默认10",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_answer",
            "description": (
                "评估 AI 回答的质量。使用 LLM-as-Judge 从准确性、完整性、实用性、表达质量"
                "四个维度打分（0-10 分），可用于自检和回答质量监控。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户的原始问题",
                    },
                    "answer": {
                        "type": "string",
                        "description": "AI 生成的回答内容",
                    },
                    "ground_truth": {
                        "type": "string",
                        "description": "可选的标准答案或参考信息",
                    },
                },
                "required": ["question", "answer"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# AgentV2
# ---------------------------------------------------------------------------

class AgentV2:
    """基于 Function Calling 的新版 Agent。

    支持多轮对话：传入 conversation_history 即可。
    支持工具链式调用：LLM 可以在一轮对话中连续调用多个工具。
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """主入口：处理用户消息并返回 Agent 回答。

        Parameters
        ----------
        user_message : str
            用户的输入消息。
        conversation_history : list[dict] | None
            之前的对话历史 (OpenAI messages 格式)。

        Returns
        -------
        dict
            {
                "answer": str,           # 最终回答
                "agent_trace": list,     # 工具调用轨迹
                "total_iterations": int, # 迭代次数
            }
        """
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        trace: list[dict] = []
        final_answer = ""
        actual_iterations = 0

        for iteration in range(self.max_iterations):
            actual_iterations = iteration + 1
            # 1. 调用 LLM（携带 tools 定义）
            response = call_llm_with_tools(messages, tools=AGENT_TOOLS)

            # 检查错误
            content = response.get("content", "") or ""
            if content.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:")):
                final_answer = f"LLM 调用出错: {content}"
                break

            tool_calls = response.get("tool_calls")

            # 2. 如果 LLM 不需要调用工具，直接回复
            if not tool_calls:
                final_answer = content
                messages.append({"role": "assistant", "content": content})
                break

            # 3. 将 assistant 的 tool_calls 消息追加到对话
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            # 4. 逐个执行工具调用
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                call_id = tool_call.get("id", "")

                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    func_args = {}

                # 执行对应工具
                result = self._execute_tool(func_name, func_args)

                trace.append({
                    "iteration": actual_iterations,
                    "tool": func_name,
                    "args": func_args,
                    "result_preview": _truncate(str(result), 300),
                    "call_id": call_id,
                })

                # 将工具结果作为 tool message 返回给 LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        else:
            # 达到最大迭代次数
            if not final_answer:
                final_answer = (
                    "我已完成了工具调用分析。以下是执行过程：\n"
                    + "\n".join(
                        f"  {i+1}. {t['tool']}({_format_args(t['args'])})"
                        for i, t in enumerate(trace)
                    )
                )

        return {
            "answer": final_answer,
            "agent_trace": trace,
            "total_iterations": actual_iterations,
            "conversation_messages": messages,
        }

    def chat_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ):
        """流式对话生成器 — 逐事件 yield 结果。

        Yields
        ------
        dict events:
            {"type": "trace", "step": {...}}      工具调用轨迹
            {"type": "token", "token": "..."}      流式文本 token
            {"type": "answer", "answer": "..."}    完整最终回答
        """
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        trace: list[dict] = []
        full_answer = ""
        actual_iterations = 0

        for iteration in range(self.max_iterations):
            actual_iterations = iteration + 1

            # 工具调用阶段使用非流式（需要完整 JSON 解析 tool_calls）
            response = call_llm_with_tools(messages, tools=AGENT_TOOLS)

            content = response.get("content", "") or ""
            if content.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:")):
                yield {"type": "answer", "answer": f"LLM 调用出错: {content}"}
                return

            tool_calls = response.get("tool_calls")

            # 无工具调用 → 这是最终回答，改用流式重新请求以逐 token 输出
            if not tool_calls:
                client = LLMClient.from_env()
                accumulated = ""
                for token in client.call_llm_stream(messages):
                    if token.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:")):
                        # 流式失败，退化为非流式结果
                        accumulated = content
                        break
                    accumulated += token
                    yield {"type": "token", "token": token}

                full_answer = accumulated
                messages.append({"role": "assistant", "content": full_answer})
                break

            # 有工具调用 → 非流式处理
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                call_id = tool_call.get("id", "")
                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    func_args = {}

                result = self._execute_tool(func_name, func_args)

                step = {
                    "iteration": actual_iterations,
                    "tool": func_name,
                    "args": func_args,
                    "result_preview": _truncate(str(result), 300),
                    "call_id": call_id,
                }
                trace.append(step)
                yield {"type": "trace", "step": step}

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        else:
            if not full_answer:
                full_answer = (
                    "我已完成了工具调用分析。以下是执行过程：\n"
                    + "\n".join(
                        f"  {i+1}. {t['tool']}({_format_args(t['args'])})"
                        for i, t in enumerate(trace)
                    )
                )

        yield {
            "type": "answer",
            "answer": full_answer,
            "agent_trace": trace,
            "total_iterations": actual_iterations,
        }

    # -------------------------------------------------------------------
    # 工具执行器
    # -------------------------------------------------------------------

    def _execute_tool(self, func_name: str, args: dict) -> Any:
        """根据函数名分发到对应工具实现。"""
        try:
            if func_name == "search_records":
                return self._exec_search_records(args)
            elif func_name == "search_graph":
                return self._exec_search_graph(args)
            elif func_name == "analyze_data":
                return self._exec_analyze_data(args)
            elif func_name == "generate_report":
                return self._exec_generate_report(args)
            elif func_name == "list_records":
                return self._exec_list_records(args)
            elif func_name == "evaluate_answer":
                return self._exec_evaluate_answer(args)
            else:
                return {"error": f"未知工具: {func_name}"}
        except Exception as exc:
            logger.exception(f"工具 {func_name} 执行失败")
            return {"error": f"工具执行异常: {exc}"}

    def _exec_search_records(self, args: dict) -> list[dict]:
        """执行混合搜索。"""
        query = args.get("query", "")
        top_k = args.get("top_k", 5)

        # 优先使用混合搜索，退化为关键词搜索
        results = hybrid_search(query, RECORDS_DIR, top_k=top_k)

        # 精简返回字段
        simplified = []
        for r in results[:top_k]:
            simplified.append({
                "id": r.get("id", ""),
                "task": r.get("task", ""),
                "dataset": r.get("dataset", ""),
                "model": r.get("model", ""),
                "matched_fields": r.get("matched_fields", []),
                "snippet": r.get("snippet", ""),
                "score": r.get("score", 0),
                "source": r.get("source", "keyword"),
                "filename": r.get("filename", ""),
            })

        return simplified

    def _exec_search_graph(self, args: dict) -> list[dict]:
        """在知识图谱中搜索。"""
        query = args.get("query", "")
        results = search_graph(query)

        simplified = []
        for r in results[:10]:
            simplified.append({
                "kind": r.get("kind", ""),
                "type": r.get("type", ""),
                "name": r.get("name", ""),
                "summary": r.get("summary", ""),
            })

        return simplified

    def _exec_analyze_data(self, args: dict) -> dict:
        """执行数据分析。"""
        record_ids = args.get("record_ids", [])
        analysis_type = args.get("analysis_type", "summary")
        return analyze_data(record_ids, analysis_type)

    def _exec_generate_report(self, args: dict) -> dict:
        """生成报告。"""
        record_id = args.get("record_id", "")

        # 加载记录
        candidates = list(RECORDS_DIR.glob(f"*{record_id}*.json")) if RECORDS_DIR.exists() else []
        if not candidates:
            return {"error": f"未找到记录: {record_id}"}

        try:
            record = json.loads(candidates[0].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {"error": f"读取记录失败: {exc}"}

        report_md = generate_markdown_report(record)
        return {
            "record_id": record.get("id", record_id),
            "report": report_md,
            "task": record.get("task", ""),
        }

    def _exec_list_records(self, args: dict) -> dict:
        """列出所有实验记录摘要。"""
        limit = args.get("limit", 10)

        if not RECORDS_DIR.exists():
            return {"records": [], "total": 0}

        records = []
        for f in sorted(RECORDS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                records.append({
                    "id": data.get("id", f.stem),
                    "task": data.get("task", ""),
                    "dataset": data.get("dataset", ""),
                    "model": data.get("model", ""),
                    "created_at": data.get("created_at", ""),
                })
            except (json.JSONDecodeError, KeyError):
                records.append({
                    "id": f.stem,
                    "task": "",
                    "dataset": "",
                    "model": "",
                    "created_at": "",
                })

            if len(records) >= limit:
                break

        return {"records": records, "total": len(records)}

    def _exec_evaluate_answer(self, args: dict) -> dict:
        """评估回答质量。"""
        question = args.get("question", "")
        answer = args.get("answer", "")
        ground_truth = args.get("ground_truth")
        return evaluate_answer(question, answer, ground_truth)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_args(args: dict) -> str:
    """格式化参数用于 trace 显示。"""
    parts = []
    for k, v in args.items():
        v_str = str(v)
        if len(v_str) > 40:
            v_str = v_str[:37] + "..."
        parts.append(f"{k}={v_str}")
    return ", ".join(parts)
