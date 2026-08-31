# Open Research Stack 开源生态集成评估与架构矩阵

本文档对 ResearchOS (Experiment Agent V2.2) 集成成熟开源科研工具与数据栈进行全面技术审计与架构评估。

---

## 1. 评估原则与核心架构定位

ResearchOS 的核心定位是 **科研上下文层、决策推演层与研究记忆中枢**，负责维护：
- Research Question (核心科学问题)
- Hypothesis (科学假说状态机)
- Evidence (支撑/反驳事实链条)
- Experiment Protocol & Physical Runs (方案与执行解耦)
- Conclusion (证据锚定的科研结论)
- Next Research Action (强论据驱动的决策闭环)
- Research Memory (跨周期科研记忆)

开源工具是底层能力提供者（文献元数据、局部数据处理、计算沙箱、实验追踪），**所有外部开源工具必须通过 ResearchOS 统一的 Adapter 接口与 ToolRegistry 接入，绝不允许外部系统反向侵入 Domain 领域模型**。

```
                         ResearchOS
                             │
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   Research Workspace   Research Intelligence   Research Graph
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ↓
                       Research Agent
                             │
                  ToolRegistry / Adapter
                             │
       ┌──────────────┬──────┼──────────────┐
       ↓              ↓      ↓              ↓
  Literature        Data   Notebook      Execution
       │              │      │              │
   OpenAlex         Pandas Jupyter       MLflow
   arXiv            DuckDB                Docker
   Semantic         Polars
   Scholar
```

---

## 2. 开源项目技术评估矩阵

| 项目 | 分类与用途 | 当前是否需要 | 集成方式 | 优先级 | 技术风险与依赖评估 |
|---|---|---|---|---|---|
| **OpenAlex** | 全球学术文献元数据检索与引用图谱 | **YES** | `LiteratureProvider` Adapter | **P0** | **LOW**：完全免费公开 REST API，支持 Polite Pool 邮箱提速，元数据规范完整。 |
| **arXiv** | 预印本论文检索与 PDF 链接获取 | **YES** | `LiteratureProvider` Adapter | **P0** | **LOW**：官方免费 Export API (Atom/XML)，轻量易解析，涵盖物理/数学/CS 前沿。 |
| **DuckDB** | 进程内极速 SQL 分析引擎 (CSV/Parquet) | **YES** | Local Engine Adapter | **P0** | **LOW**：轻量 C/Python 绑定，无独立守护进程，本地文件极速聚合与查询，Local-First 完美契合。 |
| **Semantic Scholar** | 语义文献关联与推荐 | **YES** | `LiteratureProvider` Adapter | **P1** | **LOW**：官方公开 Graph API，适合获取语义相关文献推荐。 |
| **Jupyter** | 交互式 Notebook 产物解析与元数据提取 | **YES** | `NotebookAdapter` | **P1** | **MEDIUM**：解析 `.ipynb` JSON 结构，关联 Cell 执行与 Artifact，无需内嵌重型 JupyterLab 前端。 |
| **MLflow** | 外部模型训练与超参追踪同步 | **MAYBE** | `MLflowAdapter` | **P1** | **MEDIUM**：读取已有 MLflow 跟踪服务中的 Runs/Params/Metrics，映射同步至 ResearchOS Runs。 |
| **PaperQA2** | 论文全文检索与严谨证据生成 | **MAYBE** | Optional Service | **P1** | **MEDIUM**：全文解析依赖重，需大型 LLM 与 Embedding 支持，作为技术调研与可选扩展模块保留。 |
| **eLabFTW** | 湿实验实验室样本与资源管理 | **LATER** | Schema Mapping | **P2** | **MEDIUM**：针对生物化学等湿实验资源协议，目前保持数据模型映射定义，不强行依赖服务端部署。 |
| **Docker** | 强物理隔离执行沙箱 | **LATER** | `ExecutionRunner` 抽象 | **P2** | **HIGH**：依赖 Docker 守护进程与系统权限，当前以 `RestrictedPythonRunner` 为默认，预留标准 Docker 接口。 |
| **MCP (Model Context Protocol)** | 统一 Agent 工具生态标准 | **LATER** | ToolRegistry 导出器 | **P3** | **MEDIUM**：保持 ToolRegistry 自有标准，未来提供 Tool $\to$ MCP 导出映射，当前不引入 MCP 服务。 |

---

## 3. 分阶段实施策略 (Phased Implementation)

### 阶段 P0：核心文献与数据栈 (Core Open Research Stack)
1. **统一 Literature Provider 架构 (`backend/integrations/literature/`)**：
   - 实现抽象基类 `LiteratureProvider`；
   - 实现 `OpenAlexProvider`、`ArxivProvider`、`SemanticScholarProvider`；
   - 增加本地 LRU 缓存、请求超时控制、指数退避重试与离线优雅降级；
   - 暴露 `search_papers`, `read_paper`, `search_related_papers` 标准低风险 Agent 工具；
   - 实现 Paper 保存为 Project 实体、关联 Evidence 与 Research Graph。
2. **本地数据分析与 DuckDB 集成 (`backend/integrations/data/`)**：
   - 抽象 `Dataset` 核心实体；
   - 实现 DuckDB 极简分析适配器，支持对本地 CSV / Parquet 执行安全 SQL 查询与统计汇总；
   - 保持与 Python Sandbox、Artifact 深度联动。

### 阶段 P1：交互计算与外部追踪 (Notebook & Tracking Adapters)
1. **Jupyter Notebook Adapter (`backend/integrations/notebook/jupyter.py`)**：
   - 提取 `.ipynb` 代码单元、输出图表与 Markdown 文本；
   - 将 Notebook 注册为标准 Artifact (`type: notebook`, `mime_type: application/x-ipynb+json`)。
2. **MLflow Run Adapter (`backend/integrations/experiment/mlflow.py`)**：
   - 读取 MLflow Client / 本地 tracking 目录中的 Runs、超参及指标，一键同步至 ResearchOS Experiment Runs。
3. **PaperQA2 技术调研报告 (`docs/paperqa2_integration.md`)**。

### 阶段 P2 / P3：长期演进与沙箱强化 (Long-Term Roadmap)
- 定义 `DockerRunner` 接口规范；
- 预留 MCP 工具协议转换网关。
