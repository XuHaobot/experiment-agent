"""
AgentV2 — 基于 ToolRegistry 与 Function Calling 的 AI 原生科研助手。

所有工具统一通过 backend.agent.tools.registry.registry 注册并调度，
完全消除 if-elif 硬编码双轨制分发。
"""

import json
import logging
from typing import Any

from src.llm_client import call_llm_with_tools, LLMClient, build_llm_client
from backend.agent.tools.registry import registry

logger = logging.getLogger(__name__)

# 向后兼容导出（动态从 Registry 获取）
def get_agent_tools() -> list[dict]:
    return registry.to_openai_tools()

# 全局兼容引用
AGENT_TOOLS = registry.to_openai_tools()


# ---------------------------------------------------------------------------
# AgentV2
# ---------------------------------------------------------------------------

class AgentV2:
    """基于 ToolRegistry 与 Function Calling 的 Agent。

    支持多轮对话与工具链式调用，所有工具执行经过统一安全/风控/审计层。
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.embedding_config = None

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        llm_config: dict | None = None,
        embedding_config: dict | None = None,
    ) -> dict:
        """主入口：处理用户消息并返回 Agent 回答。"""
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        trace: list[dict] = []
        final_answer = ""
        actual_iterations = 0
        self.embedding_config = embedding_config

        tools = registry.to_openai_tools()

        for iteration in range(self.max_iterations):
            actual_iterations = iteration + 1
            # 1. 调用 LLM（携带 Registry 导出的 tools 定义）
            response = call_llm_with_tools(messages, tools=tools, llm_config=llm_config)

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

            # 3. 记录 assistant 消息（含 tool_calls）
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            # 4. 执行工具调用（统一走 Registry）
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                call_id = tool_call.get("id", "")
                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    func_args = {}

                result = self._execute_tool(func_name, func_args)

                # 记录 trace
                trace.append({
                    "iteration": actual_iterations,
                    "tool": func_name,
                    "args": func_args,
                    "result_preview": _truncate(str(result), 300),
                    "call_id": call_id,
                })

                # 将工具返回写回 messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        else:
            # 达到最大迭代次数
            if not final_answer:
                final_answer = (
                    "我已完成多轮分析，但达到了最大推理步数上限。以下是执行过程：\n"
                    + "\n".join(
                        f"  {i+1}. {t['tool']}({_format_args(t['args'])})"
                        for i, t in enumerate(trace)
                    )
                )

        return {
            "answer": final_answer,
            "agent_trace": trace,
            "total_iterations": actual_iterations,
        }

    def chat_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        llm_config: dict | None = None,
        embedding_config: dict | None = None,
    ):
        """流式对话生成器 — 逐事件 yield 结果。"""
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        trace: list[dict] = []
        full_answer = ""
        actual_iterations = 0
        self.embedding_config = embedding_config
        tools = registry.to_openai_tools()

        for iteration in range(self.max_iterations):
            actual_iterations = iteration + 1

            # 工具调用阶段使用非流式
            response = call_llm_with_tools(messages, tools=tools, llm_config=llm_config)

            content = response.get("content", "") or ""
            if content.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:")):
                yield {"type": "answer", "answer": f"LLM 调用出错: {content}"}
                return

            tool_calls = response.get("tool_calls")

            # 无工具调用 → 流式输出最终回答
            if not tool_calls:
                client = build_llm_client(llm_config)
                accumulated = ""
                for token in client.call_llm_stream(messages):
                    if token.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:")):
                        accumulated = content
                        break
                    accumulated += token
                    yield {"type": "token", "token": token}

                full_answer = accumulated
                messages.append({"role": "assistant", "content": full_answer})
                break

            # 有工具调用
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
    # 工具执行器 — 统一由 ToolRegistry 接管分发与安全检查
    # -------------------------------------------------------------------

    def _execute_tool(self, func_name: str, args: dict) -> Any:
        """统一通过 ToolRegistry 执行，不再使用 if-elif 硬编码。"""
        return registry.call(func_name, caller="agent_v2", **args)


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
