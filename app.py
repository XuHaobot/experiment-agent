import json
from pathlib import Path

import streamlit as st

from src.agent import ExperimentAgent
from src.graph.builder import build_graph_from_record
from src.graph.query import search_graph
from src.graph.store import save_graph
from src.graph.visualize import generate_graph_html
from src.llm_client import LLMClient
from src.reader import read_uploaded_file
from src.storage import (
    DATA_DIR,
    ensure_storage_dirs,
    save_raw_text,
    save_record,
    save_report,
)
from src.tools.report_tool import generate_markdown_report
from src.tools.search_tool import search_records


st.set_page_config(
    page_title="实验记录整理 Agent",
    layout="wide",
)


def render_search_panel(records_dir: Path) -> None:
    st.sidebar.header("实验记忆")
    record_count = len(list(records_dir.glob("*.json"))) if records_dir.exists() else 0
    st.sidebar.caption(f"本地历史记录：{record_count} 条")

    keyword = st.sidebar.text_input("关键词搜索", placeholder="例如：CUDA / batch_size / ResNet")

    if not keyword:
        st.sidebar.caption(
            "搜索范围：task、dataset、model、commands、params、errors、solutions、conclusion、next_step。"
        )
        return

    results = search_records(keyword, records_dir)
    if not results:
        st.sidebar.info("没有找到匹配记录。")
        return

    st.sidebar.success(f"找到 {len(results)} 条匹配记录")
    for item in results:
        title = item.get("filename") or item.get("id", "未命名记录")
        with st.sidebar.expander(title):
            st.write(f"Dataset：`{item.get('dataset') or '未识别'}`")
            st.write(f"Model：`{item.get('model') or '未识别'}`")

            matched_fields = item.get("matched_fields", [])
            if matched_fields:
                st.markdown("命中字段：" + " ".join(f"`{field}`" for field in matched_fields))

            st.markdown("**简短内容**")
            st.caption(item.get("snippet") or "无摘要")
            st.caption(str(item.get("path", "")))


def render_llm_status() -> None:
    client = LLMClient.from_env()
    if client.is_configured:
        st.success(f"LLM API 已配置，将使用模型 `{client.model}` 进行增强抽取。")
        return

    st.warning("当前未配置 LLM API，将使用规则抽取结果。配置 .env 后可启用 LLM 增强抽取。")


def render_llm_run_metadata(record: dict) -> None:
    metadata = record.get("metadata", {})
    llm_used = bool(metadata.get("llm_used"))
    llm_error = metadata.get("llm_error")

    st.subheader("LLM 抽取状态")
    col_used, col_error = st.columns([1, 3])
    with col_used:
        st.metric("metadata.llm_used", str(llm_used))
    with col_error:
        if llm_used:
            st.success("本次分析已启用 LLM 增强抽取。")
        else:
            st.info("本次分析使用规则抽取结果。")
            if llm_error:
                st.caption(f"LLM 状态：{llm_error}")


def render_agent_trace(record: dict) -> None:
    trace = record.get("agent_trace", {})
    selected_tools = trace.get("selected_tools", [])
    steps = trace.get("steps", [])

    st.subheader("Agent 分析过程")

    st.markdown("**选择的工具**")
    if selected_tools:
        st.write(" ".join(f"`{tool}`" for tool in selected_tools))
    else:
        st.caption("未选择额外工具。")

    st.markdown("**工具调用步骤**")
    if steps:
        st.dataframe(
            [
                {
                    "步骤": index,
                    "工具": step.get("tool", ""),
                    "状态": step.get("status", ""),
                    "摘要": step.get("detail", ""),
                }
                for index, step in enumerate(steps, start=1)
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("暂无工具调用记录。")


def render_graph_area(graph: dict, graph_path: str) -> None:
    st.subheader("实验知识图谱")
    st.caption(f"图谱 JSON：`{graph_path}`")

    entities = graph.get("entities", [])
    relations = graph.get("relations", [])
    st.write(f"实体数量：`{len(entities)}`，关系数量：`{len(relations)}`")

    col_entities, col_relations = st.columns(2)
    with col_entities:
        st.markdown("**实体列表**")
        st.dataframe(
            [
                {
                    "id": entity.get("id", ""),
                    "type": entity.get("type", ""),
                    "name": entity.get("name", ""),
                }
                for entity in entities
            ],
            hide_index=True,
            use_container_width=True,
        )

    with col_relations:
        st.markdown("**关系列表**")
        st.dataframe(
            [
                {
                    "source": relation.get("source", ""),
                    "target": relation.get("target", ""),
                    "type": relation.get("type", ""),
                }
                for relation in relations
            ],
            hide_index=True,
            use_container_width=True,
        )

    if st.button("生成知识图谱可视化"):
        result = generate_graph_html(graph)
        if result.get("ok"):
            st.success(f"已生成图谱 HTML：`{result['path']}`")
        else:
            st.warning(result.get("error", "图谱可视化生成失败。"))

    keyword = st.text_input("图谱关键词查询", placeholder="例如：CUDA / batch / SOLVED_BY")
    if keyword:
        results = search_graph(keyword)
        if not results:
            st.info("没有找到匹配的图谱实体或关系。")
        else:
            st.write(f"找到 {len(results)} 条图谱匹配结果")
            st.dataframe(
                [
                    {
                        "kind": item.get("kind", ""),
                        "type": item.get("type", ""),
                        "name": item.get("name", ""),
                        "summary": item.get("summary", ""),
                        "graph": item.get("graph_path", ""),
                    }
                    for item in results
                ],
                hide_index=True,
                use_container_width=True,
            )


def render_downloads(record: dict, report: str) -> None:
    record_id = record.get("id") or "experiment-record"
    json_text = json.dumps(record, ensure_ascii=False, indent=2)

    col_json, col_report = st.columns(2)
    with col_json:
        st.download_button(
            "下载 JSON 记录",
            data=json_text,
            file_name=f"{record_id}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_report:
        st.download_button(
            "下载 Markdown 报告",
            data=report,
            file_name=f"{record_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )


def render_saved_paths(raw_path: Path, record_path: Path, report_path: Path, graph_path: str) -> None:
    st.subheader("保存位置")
    st.write(f"原始文件：`{raw_path}`")
    st.write(f"JSON 记录：`{record_path}`")
    st.write(f"Markdown 报告：`{report_path}`")
    st.write(f"图谱 JSON：`{graph_path}`")


def main() -> None:
    ensure_storage_dirs()

    st.title("基于 Agent 的实验记录整理与调参复盘助手")
    st.caption("上传实验聊天记录或日志，生成结构化 JSON、Markdown 复盘报告和轻量知识图谱。")

    render_search_panel(DATA_DIR / "records")
    render_llm_status()

    uploaded_file = st.file_uploader(
        "上传实验记录文件",
        type=["txt", "md", "json"],
        help="第一版支持 txt / md / json，内容会保存在本地 data/raw。",
    )

    if uploaded_file is None:
        st.info("请上传一个实验记录文件，或查看 examples/sample_chat.txt 准备样例。")
        return

    text = read_uploaded_file(uploaded_file)
    st.subheader("原始内容预览")
    st.text_area("内容", text[:10000], height=280, label_visibility="collapsed")

    if st.button("开始分析", type="primary"):
        raw_path = save_raw_text(uploaded_file.name, text)

        agent = ExperimentAgent()
        record = agent.analyze(text, source_name=uploaded_file.name)
        record_path = save_record(record)

        report = generate_markdown_report(record)
        report_path = save_report(record["id"], report)

        graph = build_graph_from_record(record)
        graph_path = save_graph(graph)

        st.session_state["last_result"] = {
            "record": record,
            "report": report,
            "graph": graph,
            "raw_path": raw_path,
            "record_path": record_path,
            "report_path": report_path,
            "graph_path": graph_path,
        }

        st.success("分析完成，已保存 JSON、Markdown 报告和图谱 JSON。")

    result = st.session_state.get("last_result")
    if not result:
        return

    record = result["record"]
    report = result["report"]
    graph = result["graph"]

    render_llm_run_metadata(record)
    render_agent_trace(record)
    render_graph_area(graph, result["graph_path"])

    tab_json, tab_report, tab_files = st.tabs(["最终 JSON", "Markdown 复盘报告", "文件与下载"])

    with tab_json:
        st.json(record)

    with tab_report:
        st.markdown(report)

    with tab_files:
        render_downloads(record, report)
        render_saved_paths(
            result["raw_path"],
            result["record_path"],
            result["report_path"],
            result["graph_path"],
        )


if __name__ == "__main__":
    main()
