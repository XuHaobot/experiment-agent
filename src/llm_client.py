import json
import os
import re
from dataclasses import dataclass

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is listed in requirements.
    load_dotenv = None

from src.utils import PROJECT_ROOT


if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")


JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)\s*```", re.IGNORECASE | re.DOTALL)


@dataclass
class LLMClient:
    """Small OpenAI-compatible Chat Completions client."""

    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "LLMClient":
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def call_llm(self, prompt: str) -> str:
        if not self.is_configured:
            return (
                "LLM_CONFIG_ERROR: LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL "
                "must be configured before calling the LLM."
            )

        url = _chat_completions_url(self.base_url)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            return f"LLM_API_ERROR: request failed: {exc}"

        if response.status_code >= 400:
            return f"LLM_API_ERROR: HTTP {response.status_code}: {response.text[:500]}"

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return f"LLM_RESPONSE_ERROR: unexpected response format: {exc}"

    def call_llm_stream(self, messages: list[dict], tools: list[dict] | None = None):
        """流式调用 LLM API，逐行 yield SSE delta 文本。

        对于带 tools 的请求（function calling），API 通常会返回完整 JSON 而非流式，
        此时自动退化为单次 yield 完整内容。
        """
        if not self.is_configured:
            yield "LLM_CONFIG_ERROR: LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL must be configured."
            return

        url = _chat_completions_url(self.base_url)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = requests.post(url, headers=headers, json=payload,
                                     timeout=self.timeout, stream=True)
        except requests.RequestException as exc:
            yield f"LLM_API_ERROR: request failed: {exc}"
            return

        if response.status_code >= 400:
            yield f"LLM_API_ERROR: HTTP {response.status_code}: {response.text[:500]}"
            return

        # 有些 API 即使请求 stream=true 也返回完整 JSON（特别是 function calling 场景）
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" not in content_type:
            try:
                data = response.json()
                message = data["choices"][0]["message"]
                content = message.get("content", "")
                if content:
                    yield content
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                yield f"LLM_RESPONSE_ERROR: unexpected response format: {exc}"
            return

        # 解析 SSE 流
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if not raw_line.startswith("data: "):
                continue
            data_str = raw_line[6:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


def call_llm(prompt: str) -> str:
    """Call the configured OpenAI-compatible LLM and return raw text."""
    return LLMClient.from_env().call_llm(prompt)


def call_llm_with_tools(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.1,
) -> dict:
    """调用带 tools 参数的 LLM API（OpenAI Function Calling 格式）。

    Parameters
    ----------
    messages : list[dict]
        OpenAI 格式的对话消息列表。
    tools : list[dict] | None
        OpenAI function calling 格式的 tools 定义。
    temperature : float
        采样温度。

    Returns
    -------
    dict
        LLM 返回的 message 对象（可能包含 content 和/或 tool_calls）。
        如果出错，返回 {"content": "ERROR: ...", "tool_calls": None}。
    """
    client = LLMClient.from_env()
    if not client.is_configured:
        return {
            "content": "LLM_CONFIG_ERROR: LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL must be configured.",
            "tool_calls": None,
        }

    url = _chat_completions_url(client.base_url)
    headers = {
        "Authorization": f"Bearer {client.api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": client.model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=client.timeout)
    except requests.RequestException as exc:
        return {"content": f"LLM_API_ERROR: request failed: {exc}", "tool_calls": None}

    if response.status_code >= 400:
        return {
            "content": f"LLM_API_ERROR: HTTP {response.status_code}: {response.text[:500]}",
            "tool_calls": None,
        }

    try:
        data = response.json()
        message = data["choices"][0]["message"]
        # 确保返回结构统一
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls"),
            "role": message.get("role", "assistant"),
        }
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return {"content": f"LLM_RESPONSE_ERROR: unexpected response format: {exc}", "tool_calls": None}


def parse_json_response(content: str) -> tuple[dict | None, str | None]:
    """Parse LLM JSON output, accepting fenced ```json blocks."""
    if _looks_like_error(content):
        return None, content

    candidate = _strip_json_fence(content)
    parsed, error = _loads_json_object(candidate)
    if parsed is not None:
        return parsed, None

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        parsed, fallback_error = _loads_json_object(candidate[start : end + 1])
        if parsed is not None:
            return parsed, None
        error = fallback_error

    return None, f"JSON_PARSE_ERROR: {error}"


def _chat_completions_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    match = JSON_BLOCK_PATTERN.search(stripped)
    if match:
        return match.group("body").strip()
    return stripped


def _loads_json_object(content: str) -> tuple[dict | None, str | None]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, str(exc)

    if not isinstance(parsed, dict):
        return None, "LLM output must be a JSON object."

    return parsed, None


def _looks_like_error(content: str) -> bool:
    return content.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "LLM_RESPONSE_ERROR:"))
