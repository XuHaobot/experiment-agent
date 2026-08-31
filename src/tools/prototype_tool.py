"""画原型图工具：根据文字描述生成结构化 UI 线框 JSON。

设计原则：
- 启发式解析（不依赖 LLM）保证离线可用、零成本。
- 检测到 UI 关键词自动映射成线框区块（导航/搜索/列表/表单/图表/卡片...）。
- 若传入 llm_config（BYOK），用 LLM 精修结构；失败则回退到启发式结果，
  绝不让工具因为网络/Key 问题而整体报错。
"""

from __future__ import annotations

import json
import re

# 关键词 -> 线框区块定义。每个区块含 type / label / 默认子项。
BLOCK_RULES: list[dict] = [
    {"kw": ["导航", "导航栏", "顶栏", "菜单栏", "nav", "navbar", "header"],
     "type": "navbar", "label": "顶部导航栏",
     "items": ["首页", "我的"]},
    {"kw": ["侧边", "侧边栏", "sidebar", "抽屉", "drawer"],
     "type": "sidebar", "label": "侧边栏",
     "items": ["概览", "设置"]},
    {"kw": ["搜索", "查询", "search", "筛选", "filter"],
     "type": "search", "label": "搜索 / 筛选框", "items": []},
    {"kw": ["标签", "tab", "tabs", "分页"],
     "type": "tabs", "label": "标签切换", "items": ["全部", "进行中", "已完成"]},
    {"kw": ["列表", "list", "feed", "动态"],
     "type": "list", "label": "列表", "count": 4},
    {"kw": ["表格", "table", "数据表"],
     "type": "table", "label": "数据表格", "columns": ["名称", "状态", "时间"]},
    {"kw": ["卡片", "card", "卡片流", "grid"],
     "type": "cards", "label": "卡片流", "count": 6},
    {"kw": ["图表", "折线", "柱状", "饼图", "统计", "chart", "dashboard", "仪表盘", "大屏"],
     "type": "chart", "label": "图表区",
     "items": ["趋势折线", "占比饼图"]},
    {"kw": ["表单", "输入", "填写", "提交", "form", "登录", "注册", "login", "signup"],
     "type": "form", "label": "表单",
     "fields": ["输入框", "提交按钮"]},
    {"kw": ["详情", "detail", "profile", "资料", "信息页"],
     "type": "detail", "label": "详情面板",
     "fields": ["标题", "描述", "操作按钮"]},
    {"kw": ["设置", "setting", "配置", "偏好"],
     "type": "settings", "label": "设置项",
     "items": ["通知", "隐私", "关于"]},
    {"kw": ["头像", "avatar", "用户", "profile"],
     "type": "avatar", "label": "用户头像区", "items": []},
    {"kw": ["弹窗", "modal", "对话框", "dialog", "浮层"],
     "type": "modal", "label": "弹窗", "items": ["确认", "取消"]},
    {"kw": ["按钮", "button", "操作", "cta"],
     "type": "button", "label": "操作按钮", "items": ["主要操作"]},
]

PLATFORM_RULES = [
    (["移动端", "mobile", "app", "小程序", "手机", "h5"], "mobile"),
    (["网页", "web", "pc", "后台", "管理端", "dashboard", "大屏"], "web"),
]


def _detect_platform(text: str) -> str:
    low = text.lower()
    for kws, plat in PLATFORM_RULES:
        if any(k in text or k in low for k in kws):
            return plat
    return "mobile"


def _detect_blocks(text: str) -> list[dict]:
    """按关键词命中顺序收集线框区块，去重并保持出现顺序。"""
    blocks: list[dict] = []
    seen: set[str] = set()
    for rule in BLOCK_RULES:
        if any(k in text for k in rule["kw"]):
            if rule["type"] in seen:
                continue
            seen.add(rule["type"])
            b = {"type": rule["type"], "label": rule["label"]}
            for k in ("items", "columns", "fields", "count"):
                if k in rule:
                    b[k] = rule[k]
            blocks.append(b)
    # 没有命中任何区块时，给一个最小可用骨架
    if not blocks:
        blocks = [
            {"type": "navbar", "label": "顶部导航栏", "items": ["首页"]},
            {"type": "list", "label": "内容列表", "count": 3},
        ]
    return blocks


def _infer_title(text: str) -> str:
    # 取第一句话（句号/换行前）作为标题候选
    first_line = re.split(r"[\n。.！!]", text.strip(), maxsplit=1)[0].strip()
    if 4 <= len(first_line) <= 24:
        return first_line
    return "原型草稿"


def generate_wireframe(description: str, llm_config: dict | None = None) -> dict:
    """根据文字描述生成结构化线框。

    Returns
    -------
    dict
        {
          "title": str,
          "platform": "mobile" | "web",
          "blocks": [ {type,label,...}, ... ],
          "summary": str,
          "source": "heuristic" | "llm",
        }
    """
    text = (description or "").strip()
    if not text:
        return {"title": "空描述", "platform": "mobile", "blocks": [],
                "summary": "请提供原型描述。", "source": "heuristic"}

    platform = _detect_platform(text)
    blocks = _detect_blocks(text)
    title = _infer_title(text)
    summary = (
        f"已根据描述生成 {platform} 端线框，共 {len(blocks)} 个区块："
        + "、".join(b["label"] for b in blocks)
    )
    result = {
        "title": title,
        "platform": platform,
        "blocks": blocks,
        "summary": summary,
        "source": "heuristic",
    }

    # 可选：LLM 精修（BYOK）。失败则保留启发式结果。
    if llm_config:
        try:
            from src.llm_client import LLMClient
            client = LLMClient(
                api_key=llm_config.get("api_key", ""),
                base_url=llm_config.get("base_url", ""),
                model=llm_config.get("model", ""),
            )
            if client.is_configured:
                prompt = (
                    "你是一个 UI 原型设计助手。请把下面的产品描述转成 JSON 线框结构，"
                    "字段为 {title, platform(mobile|web), blocks:[{type,label,items?}]}。"
                    "只输出 JSON，不要解释。\n\n描述：\n" + text
                )
                raw = client.call_llm(prompt)
                if raw and not raw.startswith("LLM_"):
                    m = re.search(r"\{.*\}", raw, re.DOTALL)
                    if m:
                        refined = json.loads(m.group(0))
                        refined["source"] = "llm"
                        refined.setdefault("summary", summary)
                        return refined
        except Exception:
            # 回退到启发式，不抛出
            pass
    return result
