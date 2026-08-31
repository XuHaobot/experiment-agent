"""
Tool Registry — 全局统一工具注册表与安全执行入口

所有 Agent 工具必须通过 registry.register 注册，
Agent / 外部调用必须统一通过 registry.call() 执行，
自动集成：
- RiskLevel 校验
- Permission 校验
- HITL 人工审批强阻断 (requires_approval)
- 敏感数据截断的 Audit Log
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from backend.agent.security.risk import RiskLevel
from backend.agent.security.permission import (
    has_permission,
    PERM_READ_PROJECT,
    PERM_READ_DATASET,
    PERM_READ_EXPERIMENT,
    PERM_WRITE_EXPERIMENT,
    PERM_EXECUTE_PYTHON,
    PERM_EXECUTE_EXPERIMENT,
    PERM_WRITE_ARTIFACT,
    PERM_WRITE_CONCLUSION,
)
from backend.agent.security.audit import log_tool_call
from backend.agent.security.guard import (
    create_approval_request,
    is_approved,
)
from backend.agent.tools.base import ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        tags: list[str] | None = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        permissions: list[str] | None = None,
        requires_approval: bool = False,
    ) -> Callable:
        """装饰器：将函数注册为标准工具"""
        def decorator(fn: Callable) -> Callable:
            tool = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=fn,
                tags=tags or [],
                risk_level=risk_level,
                permissions=permissions or [],
                requires_approval=requires_approval,
            )
            self._tools[name] = tool
            logger.debug("Tool registered: %s [risk=%s, approval=%s]", name, risk_level, requires_approval)
            return fn
        return decorator

    def register_definition(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def all_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def openai_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def to_openai_tools(self) -> list[dict]:
        """动态导出为 OpenAI Tools 列表格式"""
        return [t.to_openai_schema() for t in self._tools.values()]

    def tools_by_tag(self, tag: str) -> list[ToolDefinition]:
        return [t for t in self._tools.values() if tag in t.tags]

    def call(
        self,
        name: str,
        caller: str = "agent",
        approval_id: str | None = None,
        **kwargs,
    ) -> Any:
        """
        统一工具调用入口：
        1. 检查工具是否存在
        2. 权限校验
        3. HITL 审批阻断（requires_approval）
        4. 执行 Handler
        5. 写入 Audit Log
        """
        tool = self.get(name)
        if tool is None:
            err_msg = f"未知工具: {name}"
            log_tool_call(
                caller=caller,
                tool_name=name,
                risk_level=RiskLevel.LOW,
                parameters=kwargs,
                status="failed",
                result_or_error=err_msg,
            )
            return {"error": err_msg}

        # 1. 权限检查
        if tool.permissions and not has_permission(tool.permissions):
            err_msg = f"权限不足: 执行工具 '{name}' 需要权限 {tool.permissions}"
            log_tool_call(
                caller=caller,
                tool_name=name,
                risk_level=tool.risk_level,
                parameters=kwargs,
                status="blocked",
                result_or_error=err_msg,
            )
            return {"error": err_msg, "status": "permission_denied"}

        # 2. HITL 审批检查 (HIGH risk / requires_approval)
        if tool.requires_approval:
            if not is_approved(approval_id, name):
                # 创建审批记录并强制阻断执行
                appr_record = create_approval_request(
                    tool_name=name,
                    parameters=kwargs,
                    caller=caller,
                    reason=f"High-risk operation '{name}' requires human authorization.",
                )
                log_tool_call(
                    caller=caller,
                    tool_name=name,
                    risk_level=tool.risk_level,
                    parameters=kwargs,
                    status="approval_required",
                    approval_required=True,
                    approval_id=appr_record["id"],
                    result_or_error="Blocked pending human approval",
                )
                return {
                    "status": "approval_required",
                    "approval_id": appr_record["id"],
                    "risk_level": str(tool.risk_level),
                    "tool_name": name,
                    "message": f"工具 '{name}' 为高风险操作，已创建审批工单 [{appr_record['id']}]，需要人工授权后方可执行。",
                }

        # 3. 实际执行
        try:
            result = tool.handler(**kwargs)
            log_tool_call(
                caller=caller,
                tool_name=name,
                risk_level=tool.risk_level,
                parameters=kwargs,
                status="success",
                approval_required=tool.requires_approval,
                approval_id=approval_id,
                result_or_error=result,
            )
            return result
        except Exception as e:
            logger.exception("Tool %s execution failed: %s", name, e)
            err_msg = str(e)
            log_tool_call(
                caller=caller,
                tool_name=name,
                risk_level=tool.risk_level,
                parameters=kwargs,
                status="failed",
                approval_required=tool.requires_approval,
                approval_id=approval_id,
                result_or_error=err_msg,
            )
            return {"error": err_msg}

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={list(self._tools.keys())}>"


# 全局单例
registry = ToolRegistry()


# ═══════════════════════════════════════════════════════════════
# 默认工具注册中心（自动装配所有系统级 Tool）
# ═══════════════════════════════════════════════════════════════

def _register_all_default_tools():
    from src.storage import DATA_DIR
    from src.tools.search_tool import hybrid_search, search_records as _search_rec
    from src.tools.data_analysis_tool import analyze_data as _analyze_d, evaluate_answer as _eval_ans
    from src.tools.report_tool import generate_markdown_report as _gen_report
    from src.graph.query import search_graph as _search_g
    from backend.domain.literature import search_papers as _search_lit
    from backend.domain.hypothesis import create_hypothesis as _create_hyp
    from backend.domain.next_experiment import recommend_next_experiments as _rec_next, create_experiment_from_candidate
    from backend.domain.data_agent import run_python_sandbox, execute_eda, _load_records
    from backend.domain.artifact import create_artifact as _create_art
    from backend.domain.conclusion import create_conclusion as _create_conc
    from backend.domain.run import execute_run_instance, create_run as _create_run

    RECORDS_DIR = DATA_DIR / "records"

    # 1. search_records (LOW)
    @registry.register(
        name="search_records",
        description="搜索历史实验记录。支持按任务名、数据集、模型名、参数、错误信息等字段进行关键词和语义混合检索。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或自然语言查询"},
                "top_k": {"type": "integer", "description": "返回结果数量上限，默认5", "default": 5},
            },
            "required": ["query"],
        },
        tags=["search", "records"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_search_records(query: str, top_k: int = 5):
        results = hybrid_search(query, RECORDS_DIR, top_k=top_k)
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

    # 2. search_graph (LOW)
    @registry.register(
        name="search_graph",
        description="在知识图谱中搜索相关实体和关系。支持按实体类型、名称搜索及多跳邻居扩展。",
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "description": "实体类型"},
                "name": {"type": "string", "description": "实体名称"},
                "max_depth": {"type": "integer", "description": "多跳查询深度，默认1", "default": 1},
            },
        },
        tags=["graph"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_search_graph(entity_type: str = None, name: str = None, max_depth: int = 1):
        return _search_g(entity_type=entity_type, name=name, max_depth=max_depth)

    # 3. analyze_data (LOW)
    @registry.register(
        name="analyze_data",
        description="对已有的实验记录进行数据聚合分析。",
        parameters={
            "type": "object",
            "properties": {
                "records": {"type": "array", "items": {"type": "object"}, "description": "待分析的实验记录列表"},
                "analysis_type": {"type": "string", "description": "分析类型", "default": "summary"},
            },
            "required": ["records"],
        },
        tags=["analysis"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_analyze_data(records: list[dict], analysis_type: str = "summary"):
        return _analyze_d(records, analysis_type=analysis_type)

    # 4. generate_report (LOW)
    @registry.register(
        name="generate_report",
        description="根据实验记录生成 Markdown 格式的复盘报告。",
        parameters={
            "type": "object",
            "properties": {
                "records": {"type": "array", "items": {"type": "object"}, "description": "实验记录列表"},
                "report_title": {"type": "string", "description": "报告标题"},
            },
            "required": ["records"],
        },
        tags=["report"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_generate_report(records: list[dict], report_title: str = "实验复盘报告"):
        return _gen_report(records, report_title=report_title)

    # 5. list_records (LOW)
    @registry.register(
        name="list_records",
        description="列出所有可用的实验记录概要。",
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "返回数量上限，默认20", "default": 20},
            },
        },
        tags=["records"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_list_records(limit: int = 20):
        records = []
        if RECORDS_DIR.exists():
            for f in sorted(RECORDS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                try:
                    import json
                    d = json.loads(f.read_text(encoding="utf-8"))
                    records.append({
                        "id": d.get("id", f.stem),
                        "task": d.get("task", ""),
                        "dataset": d.get("dataset", ""),
                        "model": d.get("model", ""),
                        "filename": f.name,
                    })
                except Exception:
                    pass
        return records

    # 6. evaluate_answer (LOW)
    @registry.register(
        name="evaluate_answer",
        description="评估最终回答的质量。",
        parameters={
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "待评估的回答文本"},
                "context": {"type": "string", "description": "参考上下文"},
            },
            "required": ["answer"],
        },
        tags=["eval"],
        risk_level=RiskLevel.LOW,
    )
    def _h_evaluate_answer(answer: str, context: str = ""):
        return _eval_ans(answer, context=context)

    # 7. search_papers (LOW)
    @registry.register(
        name="search_papers",
        description="在学术文献数据库（OpenAlex / Semantic Scholar）中搜索学术论文。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "source": {"type": "string", "enum": ["openalex", "semantic_scholar", "auto"], "default": "openalex"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        tags=["literature"],
        risk_level=RiskLevel.LOW,
    )
    def _h_search_papers(query: str, source: str = "openalex", limit: int = 5):
        return _search_lit(query=query, source=source, limit=limit)

    # 8. create_hypothesis (LOW / MEDIUM)
    @registry.register(
        name="create_hypothesis",
        description="为 Research Project 创建一个新的科学假说 (Hypothesis)。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "所属项目 ID"},
                "title": {"type": "string", "description": "假说简短陈述"},
                "description": {"type": "string", "description": "假说详细阐述"},
                "question_id": {"type": "string", "description": "关联的研究问题 ID（可选）"},
            },
            "required": ["project_id", "title"],
        },
        tags=["hypothesis"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_WRITE_EXPERIMENT],
    )
    def _h_create_hypothesis(project_id: str, title: str, description: str = "", question_id: str = None):
        return _create_hyp(project_id=project_id, title=title, description=description, question_id=question_id)

    # 9. recommend_next_experiment (LOW)
    @registry.register(
        name="recommend_next_experiment",
        description="基于项目历史实验与 Run 记录，用 AI 分析并推荐下一轮最值得尝试的候选实验方案。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Research Project ID"},
                "experiment_ids": {"type": "array", "items": {"type": "string"}, "description": "指定实验 ID 列表"},
                "max_candidates": {"type": "integer", "default": 3},
            },
            "required": ["project_id"],
        },
        tags=["recommendation"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_recommend_next_experiment(project_id: str, experiment_ids: list = None, max_candidates: int = 3):
        return _rec_next(project_id=project_id, experiment_ids=experiment_ids, max_candidates=max_candidates)

    # 10. run_data_analysis / run_python (MEDIUM)
    @registry.register(
        name="run_python",
        description="在安全沙箱中执行 Python 数据分析代码，支持 numpy/pandas/scipy/matplotlib。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的 Python 代码"},
                "record_ids": {"type": "array", "items": {"type": "string"}, "description": "需要分析的实验记录 ID 列表"},
                "timeout": {"type": "integer", "default": 10},
            },
            "required": ["code"],
        },
        tags=["sandbox", "python"],
        risk_level=RiskLevel.MEDIUM,
        permissions=[PERM_EXECUTE_PYTHON],
    )
    def _h_run_python(code: str, record_ids: list = None, timeout: int = 10):
        context = {}
        if record_ids:
            context["records"] = _load_records(record_ids)
        return run_python_sandbox(code, timeout=timeout, context=context)

    # 别名注册 run_data_analysis
    @registry.register(
        name="run_data_analysis",
        description="在安全沙箱中执行 Python 数据分析代码（run_python 别名）。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的 Python 代码"},
                "record_ids": {"type": "array", "items": {"type": "string"}},
                "timeout": {"type": "integer", "default": 10},
            },
            "required": ["code"],
        },
        tags=["sandbox", "python"],
        risk_level=RiskLevel.MEDIUM,
        permissions=[PERM_EXECUTE_PYTHON],
    )
    def _h_run_data_analysis(code: str, record_ids: list = None, timeout: int = 10):
        return _h_run_python(code=code, record_ids=record_ids, timeout=timeout)

    # 11. run_eda (LOW)
    @registry.register(
        name="run_eda",
        description="对指定实验记录自动执行 EDA（探索性数据分析）。",
        parameters={
            "type": "object",
            "properties": {
                "record_id": {"type": "string", "description": "实验记录 ID"},
            },
            "required": ["record_id"],
        },
        tags=["analysis"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_EXPERIMENT],
    )
    def _h_run_eda(record_id: str):
        return execute_eda(record_id)

    # 12. create_artifact (LOW)
    @registry.register(
        name="create_artifact",
        description="将实验产出（图表、代码、报告、分析结果等）注册为 Artifact 资产并建立血缘追溯。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "所属项目 ID"},
                "name": {"type": "string", "description": "Artifact 名称"},
                "artifact_type": {"type": "string", "enum": ["chart", "report", "code", "dataset", "model", "analysis", "protocol", "other"]},
                "content": {"type": "string", "description": "Artifact 内容"},
                "source_record_id": {"type": "string", "description": "来源实验记录 ID"},
            },
            "required": ["project_id", "name", "artifact_type", "content"],
        },
        tags=["artifact"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_WRITE_ARTIFACT],
    )
    def _h_create_artifact(project_id: str, name: str, artifact_type: str, content: str, source_record_id: str = None):
        return _create_art(
            project_id=project_id,
            name=name,
            artifact_type=artifact_type,
            content=content,
            source_record_id=source_record_id,
        )

    # 13. save_conclusion (LOW)
    @registry.register(
        name="save_conclusion",
        description="将 AI 分析得出的科研结论沉淀入库，并关联证据来源。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "所属项目 ID"},
                "text": {"type": "string", "description": "结论文本"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium"},
                "hypothesis_id": {"type": "string", "description": "关联的假设 ID"},
                "evidence_refs": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["project_id", "text"],
        },
        tags=["conclusion"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_WRITE_CONCLUSION],
    )
    def _h_save_conclusion(project_id: str, text: str, confidence: str = "medium", hypothesis_id: str = None, evidence_refs: list = None):
        return _create_conc(
            project_id=project_id,
            text=text,
            hypothesis_id=hypothesis_id,
            evidence_refs=evidence_refs or [],
            confidence=confidence,
            source="agent",
        )

    # 14. create_experiment (MEDIUM)
    @registry.register(
        name="create_experiment",
        description="为项目创建新的实验方案（Experiment Draft）。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID"},
                "task": {"type": "string", "description": "实验任务名称"},
                "model": {"type": "string", "description": "模型名称"},
                "dataset": {"type": "string", "description": "数据集名称"},
                "params": {"type": "object", "description": "实验参数配置"},
                "hypothesis_id": {"type": "string", "description": "关联假设 ID"},
            },
            "required": ["project_id", "task"],
        },
        tags=["experiment"],
        risk_level=RiskLevel.MEDIUM,
        permissions=[PERM_WRITE_EXPERIMENT],
    )
    def _h_create_experiment(project_id: str, task: str, model: str = "", dataset: str = "", params: dict = None, hypothesis_id: str = None):
        from backend.domain.project import add_experiment_to_project
        from src.storage import save_record
        rec = {
            "task": task,
            "model": model,
            "dataset": dataset,
            "params": params or {},
            "hypothesis_id": hypothesis_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        res = save_record(rec)
        rec_id = res.get("id", "")
        if rec_id:
            add_experiment_to_project(project_id, rec_id)
        return {"success": True, "record_id": rec_id, "experiment": rec}

    # 15. execute_run (HIGH - REQUIRES APPROVAL)
    @registry.register(
        name="execute_run",
        description="实际执行指定的实验 Run 实例（高风险物理/沙箱执行操作，必须经过人工审批）。",
        parameters={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "待执行的 ExperimentRun ID"},
                "execution_code": {"type": "string", "description": "执行脚本或代码（可选）"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["run_id"],
        },
        tags=["execution", "run"],
        risk_level=RiskLevel.HIGH,
        permissions=[PERM_EXECUTE_EXPERIMENT],
        requires_approval=True,
    )
    def _h_execute_run(run_id: str, execution_code: str = None, timeout: int = 30):
        return execute_run_instance(run_id=run_id, execution_code=execution_code, timeout=timeout)

    # 16. search_papers (LOW)
    @registry.register(
        name="search_papers",
        description="通过 OpenAlex 或 arXiv 检索相关的全球学术文献元数据与摘要。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或学术问题描述"},
                "source": {"type": "string", "enum": ["openalex", "arxiv", "semantic_scholar"], "default": "openalex", "description": "文献源"},
                "limit": {"type": "integer", "default": 5, "description": "返回条数"},
            },
            "required": ["query"],
        },
        tags=["literature", "research"],
        risk_level=RiskLevel.LOW,
        permissions=["search_literature"],
    )
    def _h_search_papers(query: str, source: str = "openalex", limit: int = 5):
        from backend.integrations.literature import search_literature
        return search_literature(query=query, source=source, limit=limit)

    # 17. read_paper (LOW)
    @registry.register(
        name="read_paper",
        description="获取单篇学术文献的详细元数据、作者、完整摘要与 PDF 链接。",
        parameters={
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "文献唯一标识 (OpenAlex ID 或 arXiv ID)"},
                "source": {"type": "string", "enum": ["openalex", "arxiv", "semantic_scholar"], "default": "openalex"},
            },
            "required": ["paper_id"],
        },
        tags=["literature", "research"],
        risk_level=RiskLevel.LOW,
        permissions=["read_literature"],
    )
    def _h_read_paper(paper_id: str, source: str = "openalex"):
        from backend.integrations.literature import get_literature_paper
        paper = get_literature_paper(paper_id=paper_id, source=source)
        return paper or {"error": f"未找到文献: {paper_id}"}

    # 18. query_dataset (LOW)
    @registry.register(
        name="query_dataset",
        description="使用 DuckDB / 本地 SQL 引擎对指定 Dataset 执行结构化 SQL 查询与统计分析。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "数据集 ID (ds_xxx)"},
                "sql": {"type": "string", "description": "SQL 查询语句（可用 dataset 或 df 作为表名）"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["dataset_id", "sql"],
        },
        tags=["data", "analytics"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_DATASET],
    )
    def _h_query_dataset(dataset_id: str, sql: str, limit: int = 50):
        from backend.domain.dataset import query_dataset_sql
        return query_dataset_sql(dataset_id=dataset_id, sql=sql, limit=limit)

    # 19. summarize_dataset (LOW)
    @registry.register(
        name="summarize_dataset",
        description="提取数据集的字段类型、空值统计与数值极值概览。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "数据集 ID (ds_xxx)"},
            },
            "required": ["dataset_id"],
        },
        tags=["data", "analytics"],
        risk_level=RiskLevel.LOW,
        permissions=[PERM_READ_DATASET],
    )
    def _h_summarize_dataset(dataset_id: str):
        from backend.domain.dataset import get_dataset_summary
        return get_dataset_summary(dataset_id=dataset_id)

    # 20. read_pdf (LOW)
    @registry.register(
        name="read_pdf",
        description="读取并提取学术论文 PDF 全文的页面、章节与段落切片结构。",
        parameters={
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "文献 ID"},
            },
            "required": ["paper_id"],
        },
        tags=["pdf", "literature"],
        risk_level=RiskLevel.LOW,
        permissions=["read_pdf"],
    )
    def _h_read_pdf(paper_id: str):
        from backend.domain.paper import get_paper_extracted_data
        data = get_paper_extracted_data(paper_id)
        return data or {"error": f"文献 {paper_id} 尚未解析 PDF 全文"}

    # 21. extract_evidence (LOW)
    @registry.register(
        name="extract_evidence",
        description="从 PDF 全文指定页面和段落中精准提取并沉淀 Evidence 证据切片。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "paper_id": {"type": "string"},
                "page": {"type": "integer"},
                "section": {"type": "string"},
                "paragraph_index": {"type": "integer"},
                "text": {"type": "string"},
                "claim": {"type": "string"},
                "hypothesis_id": {"type": "string"},
            },
            "required": ["project_id", "paper_id", "page", "section", "paragraph_index", "text"],
        },
        tags=["pdf", "evidence"],
        risk_level=RiskLevel.LOW,
        permissions=["read_pdf"],
    )
    def _h_extract_evidence(project_id: str, paper_id: str, page: int, section: str, paragraph_index: int, text: str, claim: str | None = None, hypothesis_id: str | None = None):
        from backend.domain.paper import create_paper_evidence_slice
        return create_paper_evidence_slice(
            project_id=project_id,
            paper_id=paper_id,
            page=page,
            section=section,
            paragraph_index=paragraph_index,
            text=text,
            claim=claim,
            hypothesis_id=hypothesis_id,
        )

    # 22. ask_paper (LOW)
    @registry.register(
        name="ask_paper",
        description="对已导入 PDF 的学术论文进行深度问答，并提供精确页码与章节引用定位。",
        parameters={
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": ["paper_id", "question"],
        },
        tags=["pdf", "qa"],
        risk_level=RiskLevel.LOW,
        permissions=["read_pdf"],
    )
    def _h_ask_paper(paper_id: str, question: str):
        from backend.domain.paper import ask_paper_question
        return ask_paper_question(paper_id=paper_id, question=question)

    # 23. inspect_dataset_relationship (LOW)
    @registry.register(
        name="inspect_dataset_relationship",
        description="自动比对多个数据集 Schema 并发现潜在的 JOIN 外键关联。",
        parameters={
            "type": "object",
            "properties": {
                "dataset_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["dataset_ids"],
        },
        tags=["dataset", "schema"],
        risk_level=RiskLevel.LOW,
        permissions=["analyze_dataset"],
    )
    def _h_inspect_dataset_relationship(dataset_ids: list[str]):
        from backend.domain.dataset import get_dataset
        from backend.integrations.data.relationship import relationship_inspector
        ds_list = [get_dataset(did) for did in dataset_ids if get_dataset(did)]
        return relationship_inspector.discover_relationships(ds_list)

    # 24. generate_analysis (LOW)
    @registry.register(
        name="generate_analysis",
        description="根据用户分析意图生成针对数据集的统计分析方案 (SQL与Python代码)。",
        parameters={
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "dataset_ids": {"type": "array", "items": {"type": "string"}},
                "target_metric": {"type": "string"},
                "group_col": {"type": "string"},
            },
            "required": ["intent", "dataset_ids"],
        },
        tags=["analysis", "wizard"],
        risk_level=RiskLevel.LOW,
        permissions=["analyze_dataset"],
    )
    def _h_generate_analysis(intent: str, dataset_ids: list[str], target_metric: str | None = None, group_col: str | None = None):
        from backend.integrations.data.wizard import analysis_wizard
        return analysis_wizard.generate_analysis_plan(
            intent=intent,
            dataset_ids=dataset_ids,
            target_metric=target_metric,
            group_col=group_col,
        )

    # 25. execute_analysis (MEDIUM)
    @registry.register(
        name="execute_analysis",
        description="执行统计分析方案并自动归档为 Analysis Artifact 产物。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "title": {"type": "string"},
                "dataset_id": {"type": "string"},
                "sql_query": {"type": "string"},
                "python_code": {"type": "string"},
            },
            "required": ["project_id", "title", "dataset_id", "sql_query"],
        },
        tags=["analysis", "execution"],
        risk_level=RiskLevel.MEDIUM,
        permissions=["analyze_dataset", "write_artifact"],
    )
    def _h_execute_analysis(project_id: str, title: str, dataset_id: str, sql_query: str, python_code: str | None = None):
        from backend.integrations.data.wizard import analysis_wizard
        return analysis_wizard.execute_and_create_artifact(
            project_id=project_id,
            title=title,
            dataset_id=dataset_id,
            sql_query=sql_query,
            python_code=python_code,
        )

    # 26. generate_experiment_code (LOW)
    @registry.register(
        name="generate_experiment_code",
        description="结合 Project、Hypothesis、Experiment 和 Dataset 真实上下文生成完整 Python 实验脚本。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "experiment_id": {"type": "string"},
                "hypothesis_id": {"type": "string"},
                "dataset_id": {"type": "string"},
                "custom_instructions": {"type": "string"},
            },
            "required": ["project_id", "experiment_id"],
        },
        tags=["experiment", "codegen"],
        risk_level=RiskLevel.LOW,
        permissions=["generate_code"],
    )
    def _h_generate_experiment_code(project_id: str, experiment_id: str, hypothesis_id: str | None = None, dataset_id: str | None = None, custom_instructions: str | None = None):
        from backend.domain.experiment_coder import generate_experiment_code
        return generate_experiment_code(
            project_id=project_id,
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            dataset_id=dataset_id,
            custom_instructions=custom_instructions,
        )

    # 27. run_experiment (HIGH - requires approval)
    @registry.register(
        name="run_experiment",
        description="在受控沙箱中执行生成的实验脚本，记录物理 Run 遥测并归档产物。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "experiment_id": {"type": "string"},
                "code": {"type": "string"},
            },
            "required": ["project_id", "experiment_id", "code"],
        },
        tags=["experiment", "execution"],
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        permissions=["execute_experiment"],
    )
    def _h_run_experiment(project_id: str, experiment_id: str, code: str):
        from backend.domain.experiment_coder import execute_experiment_code_safely
        return execute_experiment_code_safely(
            project_id=project_id,
            experiment_id=experiment_id,
            code=code,
        )

    # 28. debug_experiment (HIGH - requires approval)
    @registry.register(
        name="debug_experiment",
        description="针对实验运行报错进行根因分析并生成修复补丁（受限最大3次）。",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "experiment_id": {"type": "string"},
                "code": {"type": "string"},
                "error_traceback": {"type": "string"},
                "retry_count": {"type": "integer", "default": 1},
            },
            "required": ["project_id", "experiment_id", "code", "error_traceback"],
        },
        tags=["experiment", "debugger"],
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        permissions=["execute_experiment"],
    )
    def _h_debug_experiment(project_id: str, experiment_id: str, code: str, error_traceback: str, retry_count: int = 1):
        from backend.domain.experiment_coder import debug_experiment_code
        return debug_experiment_code(
            project_id=project_id,
            experiment_id=experiment_id,
            code=code,
            error_traceback=error_traceback,
            retry_count=retry_count,
        )


# 初始化注册所有默认工具
_register_all_default_tools()
