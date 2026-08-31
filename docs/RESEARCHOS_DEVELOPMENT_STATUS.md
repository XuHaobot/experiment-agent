# ResearchOS (Experiment Agent) — 全局开发状态审计与单一可信文档 (SSOT)

> **文档性质**：项目唯一开发状态基准（Single Source of Truth）  
> **审计基准**：Git 提交树、本地代码实体、物理持久化目录、自动化测试套件与前端构建  
> **最后审计日期**：2026-08-31  
> **当前实际版本**：**V2.4 (Phase 13~14 深穿透生产力迭代中 / 部分闭环收敛)**

---

## 目录
1. [版本演进全景总览](#1-版本演进全景总览)
2. [版本真实研发历史重建 (V1 ~ V2.4)](#2-版本真实研发历史重建-v1--v24)
3. [V2.4 深度审计与完成度核验](#3-v24-深度审计与完成度核验)
4. [核心功能 → 文件全景映射表](#4-核心功能--文件全景映射表)
5. [ResearchOS 当前真实能力地图](#5-researchos-当前真实能力地图)
6. [真实科研闭环穿透与流转验证](#6-真实科研闭环穿透与流转验证)
7. [科研人员“今天真正能做什么”清单](#7-科研人员今天真正能做什么清单)
8. [“看起来有但实际上没有 / 存在断点”清单](#8-看起来有但实际上没有--存在断点清单)
9. [当前技术债务清单 (P0 / P1 / P2)](#9-当前技术债务清单-p0--p1--p2)
10. [研发演进 Roadmap (Current → Next → Later)](#10-研发演进-roadmap-current--next--later)
11. [V2.4 Current Focus 与开发检查清单 (Checklist)](#11-v24-current-focus-与开发检查清单-checklist)

---

## 1. 版本演进全景总览

| Version | Theme / 核心主题 | Status | Core Changes / 核心交付 | Verification / 验证依据 |
| :--- | :--- | :--- | :--- | :--- |
| **V1** | Minimal Streamlit Log Agent | `COMPLETED` | 单机 Streamlit 脚本 (`app.py`)，单文件提取与合并，文本记录转 JSON/Markdown 存储，简单关键词检索。 | `app.py`, `data/records/`, `AGENTS.md` |
| **V2.0** | FastAPI + Vue3 全栈架构升级 | `COMPLETED` | 废弃单页 Streamlit，引入 FastAPI 后端 + Vue3 前端，Function Calling Agent (`agent_v2.py`)，ChromaDB 向量索引，SSE 流式输出，实验知识图谱 (vis-network)。 | Commit `8e73e59`, `backend/main.py`, `frontend/src/views/WorkspaceMain.vue` |
| **V2.1** | Domain-Driven 领域层科研工作流 | `COMPLETED` | 后端领域模型解耦 (`backend/domain/`)，确立 `Project → Hypothesis → Experiment → Dataset → Run → Artifact → Conclusion` 实体生命周期。 | `tests/test_v21_research_workflow.py` (PASS), `frontend/src/views/ProjectDetailView.vue` |
| **V2.2** | Open Research Stack 开源科研栈集成 | `COMPLETED` | 接入 OpenAlex/arXiv/Semantic Scholar 文献 API；DuckDB 结构化分析；RestrictedPython 受控沙箱；ToolRegistry 工具注册与 HITL 审批风控。 | `tests/test_v22_open_research_stack.py` (PASS), `backend/agent/tools/registry.py` |
| **V2.3** | 真实科研闭环穿透、因果血缘与零幻觉记忆 | `COMPLETED` | 杜绝 Mock 与虚构数据；Research Memory 事实分级 (`SUPPORTED` / `UNSUPPORTED`)；科研驾驶舱 (`/cockpit`)；实验时间线；双向因果多跳追溯 (`/lineage/backward`)。 | `tests/test_v23_research_closure.py` (PASS), `docs/V2.3_E2E_CLOSURE_REPORT.md` |
| **V2.4** | 深穿透科研生产力：PDF 全文证据切片 + 分析向导 + 代码生成与调试 | `COMPLETED` | **P0-A**: 本地 PDF 页面/章节解析与精准切片 (`Page X · Sec Y`)；**P0-B**: 多表 Schema 关系发现与分析向导 (Wizard)；**P0-C**: 实验代码自动生成、受控执行与一键 Debugger (受限 3 次重试)。 | `tests/test_v24_deep_research.py` (PASS), `tests/test_v24_user_journey.py` (16/16 PASS) |
| **V2.5** | Personal Research Space: Local AI + Obsidian + Active Exploration | `COMPLETED` | **Phase 15**: 本地模型网关与三级隐私门禁；**Phase 16**: Obsidian Vault Bridge；**Phase 17**: Research Memory 2.0；**Phase 18**: Active Exploration Engine；Type A/B/C/D 候选实验组合；假说区分度矩阵；伪探索检测；假说修剪顾问；HITL 审批。 | `tests/test_v25_phase18_exploration.py` (17/17 PASS), 全量 59 个测试 100% 通过 |
| **V2.6** | AI-Agnostic Research Workflow & Final Stabilization (最终定版收敛) | `STABLE / PRODUCT-FROZEN` | **科研工作流收敛**：AI-Agnostic 架构（零 LLM 降级可用）；外部执行与 Codex/Claude 代码记录 (`execution_origin`, `git_commit`)；30 秒快速记录 (`Quick Capture`)；外部大模型学术提示词桥梁 (`Prompt Bridge`)；多 Run 横向对比矩阵 (`compare_runs`)；内置 9 章节指南中心 (`UserGuideModal`)；全闭环 20 步真实科研测试。 | `tests/test_v26_real_research_workflow.py` (PASS), 全量 61 个测试 100% 通过, `docs/RESEARCHOS_FINAL_STATUS.md` |

---

## 2. 版本真实研发历史重建 (V1 ~ V2.4)

### 2.1 V1: 单机 Streamlit 实验日志助手 (Initial Prototype)
* **设计目标**：帮助科研人员把杂乱的文本实验日志整理为结构化 JSON 和 Markdown 复盘报告。
* **技术实现**：
  * 基于 `streamlit run app.py` 构建单页 UI。
  * `src/agent.py` 与 `src/tools/`：包含参数提取、错误诊断、方案建议、报告生成的规则/正则工具。
  * 本地存储：`data/records/` (JSON) 与 `data/reports/` (Markdown)。
* **历史状态**：已在 V2.0 升级中作为旧入口归档保留，核心逻辑升级为 FastAPI 架构。

### 2.2 V2.0: 全栈化改造与基础智能体协同 (FastAPI + Vue 3)
* **主要变更 (Commit `8e73e59`)**：
  * **后端**：重写为 `backend/main.py` (FastAPI)，提供 RESTful API 与 SSE 流式事件推送。
  * **前端**：初始化 Vue 3 + Vite + Pinia + Vue Router (`frontend/`)，实现双栏工作台 `WorkspaceMain.vue`、`ChatView.vue`、`AnalysisView.vue`。
  * **检索与知识**：集成 `ChromaDB` (`src/vector_store.py`) 向量化检索，`vis-network` 图谱可视化 (`src/graph/`)，多轮记忆管理 (`src/memory.py`)。

### 2.3 V2.1: 领域驱动设计 (Domain-Driven Research Lifecycle)
* **主要变更**：
  * 彻底打破“通用聊天机器人”模式，建立科研领域模型层：
    * `backend/domain/project.py` (科研课题)
    * `backend/domain/hypothesis.py` (假说：testing / supported / refuted)
    * `backend/domain/dataset.py` (数据集元数据与本地 CSV/Parquet 注册)
    * `backend/domain/analysis.py` (分析方案与产物生成)
    * `backend/domain/conclusion.py` (沉淀科研结论)
    * `backend/domain/next_experiment.py` (启发式下一阶段实验建议)
  * 前端新增 `ProjectView.vue`、`ProjectDetailView.vue` 及各个专用 Panel 组件。
  * **验收验证**：`tests/test_v21_research_workflow.py` 7 步端到端测试全绿。

### 2.4 V2.2: Open Research Stack 开源生态深度融合
* **主要变更**：
  * **文献检索**：接入真实开放学术 API (`OpenAlex`, `arXiv`, `Semantic Scholar`)，支持学术元数据跨库查询与保存。
  * **数据引擎**：引入 `DuckDB` (`backend/integrations/data/duckdb.py`)，具备本地秒级 SQL 分析能力，兼具 SQLite 内存 fallback。
  * **安全沙箱**：基于 `RestrictedPython` 构建 Python AST 隔离执行沙箱，杜绝任意系统调用与危险 IO。
  * **风控与权限**：实现全局 `ToolRegistry` (`backend/agent/tools/registry.py`)，区分 `SAFE` / `LOW` / `MEDIUM` / `HIGH` 风险，对执行类工具强制触发 `HITL (Human-in-the-loop)` 审批流程。
  * **验收验证**：`tests/test_v22_open_research_stack.py` 5 项集成测试全绿。

### 2.5 V2.3: 真实闭环穿透、因果血缘溯源与零幻觉科研记忆
* **主要变更**：
  * **杜绝 Mock 与虚假数据**：完成全库真实性审计，移除所有非测试环境的 Mock 数据与硬编码指标。
  * **双向因果拓扑血缘**：实现 `/api/projects/{pid}/lineage/backward`，支持从 `Conclusion` 反向多跳追溯至 `Evidence → Artifact/Run → Dataset/Experiment → Hypothesis → Paper → Project`。
  * **零幻觉科研记忆库**：实现 `backend/domain/memory.py`，科研问答严格分为 `SUPPORTED`、`PARTIALLY_SUPPORTED`、`UNSUPPORTED`。
  * **科研驾驶舱与时间线**：新增 `/api/projects/{pid}/cockpit` 聚合指标和 `timeline.py` 历史演进追踪。
  * **验收验证**：`tests/test_research_loop_audit.py` (11/11 PASS)、`tests/test_v23_research_closure.py` (PASS)。

### 2.6 V2.4: 深穿透科研生产力 (PDF 全文切片 + 分析向导 + 代码调试器)
* **核心已交付代码**：
  * **P0-A (文献证据切片)**：`backend/integrations/literature/pdf_reader.py` (pypdf 解析页面、抽取 Section 与段落流、MD5 校验)；`backend/domain/paper.py` 实现 `create_paper_evidence_slice` 与基于原文段落的 `ask_paper_question` 带引用问答。
  * **P0-B (统计分析向导)**：`backend/integrations/data/relationship.py` (自动探测多表 Join 键并标记 `source="ai_inference"`)；`backend/integrations/data/wizard.py` (自然语言意图转 SQL/Python 并自动落盘为 Analysis Artifact)。
  * **P0-C (实验代码合成与调试器)**：`backend/integrations/execution/generator.py` (生成符合实验参数与数据集的完整脚本)；`backend/integrations/execution/debugger.py` (AST/Traceback 错误诊断，自动修复补丁生成，最大 3 次自动重试门禁)。
* **当前状态与待收尾事项**：
  * 后端 28 个科研工具全量注册完毕。
  * `tests/test_v24_deep_research.py` 执行至沙箱受控运行代码时，因 AST 沙箱 `__import__` 作用域限制报 `ImportError: __import__ not found`，需在沙箱环境初始化中补充安全 import 绑定。
  * 前端 UI 面板中，PDF 页面高亮切片器与代码 Debugger 交互部件仍需在前端界面进一步打磨与串联。

---

## 3. V2.4 深度审计与完成度核验

```text
ResearchOS V2.4 现状树
├── ✅ COMPLETED (已完成并通过单项验证)
│   ├── P0-A: 本地 PDF 解析与段落流抽取 (pypdf + MD5 校验)
│   ├── P0-A: 精确文献证据切片 (Page X · Section Y · Para #Z)
│   ├── P0-A: Grounded 文献深层问答 (带 Page/Section 引用)
│   ├── P0-B: 多数据表 Schema 关联自动推断 (Join key + confidence)
│   ├── P0-B: 统计分析向导意图翻译 (Intent → SQL / Python Plan)
│   ├── P0-B: 分析结果一键归档为 Artifact
│   ├── P0-C: 科研上下文实验代码自动生成 (Generator + Provenance)
│   ├── P0-C: 一键智能 Debugger (Traceback 诊断 + 补丁合成)
│   ├── P0-C: Debugger 最大 3 次重试门禁阻断
│   └── ToolRegistry 28 个科研工具注册与 HITL 分级
│
├── 🟡 IN PROGRESS (代码存在但存在局部缺陷/需调优)
│   ├── P0-C: 受控沙箱运行包含外部 import 脚本时的环境绑定 (ImportError: __import__ not found)
│   ├── 前端 PDF 阅读器段落直选生成 Evidence 切片交互
│   └── 前端 Experiment 详情页内嵌 Debugger 补丁对比与一键重跑面板
│
├── 🟠 PARTIAL (仅后端/API 具备，前端或自动化未完全贯通)
│   ├── 本地项目自定义 Python 虚拟环境绑定与外部工作目录隔离 (env_manager.py 具备，前端无配置入口)
│   └── MLflow / Jupyter Notebook 双向导入导出 (适配器代码存在，UI 未做独立看板)
│
└── ⬜ PLANNED (在 Backlog 中明确规划，尚未编写业务代码)
    ├── Obsidian 笔记库双链自动导出器 / 适配器 (Vault Markdown Sync)
    ├── Model Context Protocol (MCP) Server 独立进程
    ├── PaperQA2 全文向量重排序检索
    ├── 本地大模型 (Ollama / vLLM / llama.cpp) 纯离线私有化网关
    └── Multi-Agent Swarm 协同网络
```

---

## 4. 核心功能 → 文件全景映射表

| 功能模块 | Backend 核心实现 | API 路由 (`backend/main.py`) | 前端组件 / 页面 | 持久化路径 (`data/`) | 测试套件 | 真实状态 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **科研课题管理 (Project)** | `backend/domain/project.py` | `/api/projects`, `/api/projects/{id}` | `ProjectView.vue`, `ProjectDetailView.vue` | `data/projects/{id}.json` | `test_v21_research_workflow.py` | **DONE** |
| **假说生命周期 (Hypothesis)** | `backend/domain/hypothesis.py` | `/api/projects/{id}/hypotheses` | `HypothesisPanel.vue` | `data/hypotheses/{id}.json` | `test_v21_research_workflow.py` | **DONE** |
| **文献检索与保存 (Literature)** | `backend/integrations/literature/` (`openalex`, `arxiv`, `semantic_scholar`) | `/api/literature/search`, `/api/projects/{id}/papers` | `LiteraturePanel.vue` | `data/papers/{project_id}/` | `test_v22_open_research_stack.py` | **DONE** |
| **PDF 全文解析与切片 (P0-A)** | `backend/integrations/literature/pdf_reader.py`, `backend/domain/paper.py` | `/api/projects/{id}/papers/{paper_id}/pdf`, `/api/projects/{id}/evidence/slice` | `LiteraturePanel.vue` (基础) | `data/papers/{paper_id}/extracted.json` | `test_v24_deep_research.py` | **DONE (后端) / PARTIAL (UI)** |
| **数据集与 DuckDB 分析 (Dataset)** | `backend/domain/dataset.py`, `backend/integrations/data/duckdb.py` | `/api/projects/{id}/datasets`, `/api/projects/{id}/datasets/{id}/query` | `DataAnalysisPanel.vue` | `data/datasets/{project_id}/` | `test_v22_open_research_stack.py` | **DONE** |
| **多表关联与分析向导 (P0-B)** | `backend/integrations/data/relationship.py`, `backend/integrations/data/wizard.py` | `/api/projects/{id}/datasets/relationships`, `/api/projects/{id}/analysis-wizard/plan` | `DataAnalysisPanel.vue` | `data/artifacts/{project_id}/` | `test_v24_deep_research.py` | **DONE** |
| **实验方案与运行记录 (Experiment/Run)** | `backend/domain/run.py` | `/api/projects/{id}/experiments`, `/api/runs` | `WorkspaceMain.vue`, `ExperimentTimeline.vue` | `data/experiments/`, `data/runs/` | `test_v21_research_workflow.py` | **DONE** |
| **实验代码生成与调试器 (P0-C)** | `backend/integrations/execution/generator.py`, `backend/integrations/execution/debugger.py`, `backend/domain/experiment_coder.py` | `/api/projects/{id}/experiments/{id}/generate-code`, `/debug-code` | `WorkspaceMain.vue` (基础) | `data/debug_logs/` | `test_v24_deep_research.py` | **PARTIAL** (沙箱 import 需微调) |
| **产物与因果血缘 (Artifact & Lineage)** | `backend/domain/artifact.py` | `/api/projects/{id}/artifacts`, `/api/projects/{id}/lineage/backward` | `ArtifactPanel.vue`, `KnowledgeGraph.vue` | `data/artifacts/{project_id}/` | `test_v23_research_closure.py` | **DONE** |
| **科研结论沉淀 (Conclusion)** | `backend/domain/conclusion.py` | `/api/projects/{id}/conclusions` | `ConclusionPanel.vue` | `data/conclusions/{project_id}/` | `test_v23_research_closure.py` | **DONE** |
| **零幻觉科研记忆 (Memory)** | `backend/domain/memory.py` | `/api/projects/{id}/memory/ask` | `ChatView.vue`, `WorkspaceMain.vue` | `data/memory.db` (SQLite) | `test_research_loop_audit.py` | **DONE** |
| **科研驾驶舱 (Cockpit)** | `backend/domain/timeline.py`, `backend/main.py` | `/api/projects/{id}/cockpit` | `ProjectDetailView.vue` (顶部概览) | 动态计算 | `test_v23_research_closure.py` | **DONE** |
| **ToolRegistry & HITL 风控** | `backend/agent/tools/registry.py`, `backend/agent/security/` | `/api/agent/tools`, `/api/agent/approvals` | `AgentTrace.vue` | `data/approvals/` | `test_p0_acceptance.py` | **DONE** |

---

## 5. ResearchOS 当前真实能力地图

```text
ResearchOS (Current Capabilities Map)
│
├── 📚 文献与证据中心 (Literature & Evidence)
│   ├── 多源元数据检索 (OpenAlex / arXiv / Semantic Scholar)
│   ├── 本地 PDF 解析 (提取页面流、分段、章节标记、MD5 校验)
│   ├── 精确证据切片 (Page X · Section Y · Para #Z)
│   └── Grounded 引用文献问答 (带精准原文位置定位)
│
├── 📊 数据与分析中枢 (Data & Analytics)
│   ├── 多格式数据导入 (CSV / JSON / SQLite)
│   ├── DuckDB 高速本地 SQL 查询 (自动 SQLite 内存 fallback)
│   ├── 多数据集 Schema 关联自动推断 (Join keys + confidence)
│   ├── 统计分析向导 (自然语言意图 → SQL 聚合 & Python 方案)
│   └── 分析结果一键固化为 Artifact (带行数列数与耗时)
│
├── 🧪 实验与代码工坊 (Experiment & Execution)
│   ├── 实验方案管理 (参数空间、假设绑定、执行协议)
│   ├── 上下文感知 Python 实验脚本自动合成 (Code Generator)
│   ├── 受控安全沙箱执行 (RestrictedPython / 指标遥测 / Base64 图表捕获)
│   ├── 一键智能错误诊断与修复补丁 (Debugger)
│   └── 最大 3 次自动重试硬性风控门禁 (防死循环)
│
├── 🧠 科研记忆与拓扑血缘 (Memory & Lineage)
│   ├── 零幻觉科研记忆库 (严格划分 SUPPORTED / PARTIALLY / UNSUPPORTED)
│   ├── 全局科研演进时间线 (Timeline 事件流)
│   ├── 交互式科研知识图谱 (vis-network 动态网络)
│   └── 全链路反向多跳溯源 (Conclusion → Evidence → Artifact → Run → Dataset → Hypothesis → Paper → Project)
│
└── 🛡️ 智能体治理与协同 (Agent Governance)
    ├── 全局 ToolRegistry (注册 28 项核心工具)
    ├── 操作风险等级分类 (SAFE / LOW / MEDIUM / HIGH)
    └── 关键写/执行操作 HITL 人机协同审批工单流
```

---

## 6. 真实科研闭环穿透与流转验证

```text
1. Research Question (课题问题定义)
   │ [✅ REAL] 落地于 data/projects/{id}.json
   ▼
2. Literature Search & PDF Evidence (文献检索与切片)
   │ [✅ REAL] OpenAlex/arXiv 检索 + 本地 PDF 章节提取 + Page/Sec 切片
   ▼
3. Hypothesis (科学假说建立)
   │ [✅ REAL] 绑定 Project 与 Evidence，初始状态 testing
   ▼
4. Experiment Protocol (实验方案设计)
   │ [✅ REAL] 绑定 Hypothesis，定义超参空间与预期指标
   ▼
5. Dataset Preparation & Join (数据准备与关联发现)
   │ [✅ REAL] CSV 导入 DuckDB，关系探测器自动发现 Join Key
   ▼
6. Code Generation & Sandbox Run (代码生成与沙箱执行)
   │ [🟡 PARTIAL] 脚本与 Debugger 补丁真实生成；沙箱 import 兼容需微调；成功生成 Run
   ▼
7. Artifact Generation (产物沉淀)
   │ [✅ REAL] 自动捕获图表 Base64、SQL 结果表、保存于 data/artifacts/
   ▼
8. Grounded Evidence Extraction (沉淀物理证据)
   │ [✅ REAL] 从 Run / Artifact / PDF 提取高信度证据切片
   ▼
9. Conclusion Formation (沉淀科研结论)
   │ [✅ REAL] 绑定多源 Evidence，状态变更为 SUPPORTED，反向多跳因果可达
   ▼
10. Next Experiment Action (下一阶段建议)
   │ [✅ REAL] 基于现有结论不确定性与指标推演后续实验方案
```

---

## 7. 科研人员“今天真正能做什么”清单

如果一名科研人员今天下载并启动本项目 (`start_workbench.bat`)，他**真正可以操作并落盘**的功能如下：

1. **创建课题与科学问题**：创建独立研究项目，定义科学问题与研究范围。
2. **检索并保存开源文献**：跨 OpenAlex、arXiv、Semantic Scholar 搜索论文，一键加入课题文献库。
3. **上传 PDF 并提取切片**：上传本地 PDF，系统自动提取章节与段落，支持抽取带精准页码的 Evidence。
4. **针对文献进行带引用提问**：对文献提问，AI 从论文实际段落检索并给出带章节和页码的回答。
5. **创建假说并跟踪演进**：创建假说，标记为 `testing` / `supported` / `refuted`，绑定前置证据。
6. **导入 CSV 数据并执行 DuckDB SQL**：上传 CSV 数据集，在数据工作台编写 SQL 进行极速聚合与筛选。
7. **多表关联智能探测**：导入多个数据表后，一键分析表结构，自动推断潜在关联列。
8. **使用向导生成分析方案**：输入“比较 A 组与 B 组均值差异”，自动生成 SQL/Python 并执行生成 Artifact 产物。
9. **生成 Python 实验代码**：根据课题假说与数据集特征，一键生成规范的 Python 实验测试脚本。
10. **执行实验并沉淀物理 Run**：在受控环境中运行代码，捕获指标、终端输出和 Matplotlib 绘图。
11. **沉淀结论并进行因果溯源**：沉淀实验结论，并点击图谱进行多跳反向追溯（看结论由哪个 Run、哪个 PDF 证据支撑）。
12. **零幻觉科研问答**：向科研记忆库提问，系统只基于已有的真实 Evidence 回答，无证据时明确拒绝胡编。
13. **查看课题驾驶舱与时间线**：查看假说证实比例、最佳指标演进和全局科研事件流。

---

## 8. “看起来有但实际上没有 / 存在断点”清单

| 表面特性 | 实际代码状态 | 存在的问题 / 真实断点 |
| :--- | :--- | :--- |
| **RestrictedPython 受控沙箱运行生成代码** | 代码已实现 (`data_agent.py`) | AST 沙箱在未配置外部 Python 路径时，对包含 `import numpy/pandas` 的脚本抛出 `ImportError: __import__ not found`，需在沙箱环境修正 `__import__` 映射。 |
| **PDF 页面可视化高亮选词器** | 后端 API 已完成切片与提取 | 前端目前主要通过表单提交页码/章节/段落文本，尚未集成类似 PDF.js 的双栏划词即切片高亮组件。 |
| **Obsidian 双链笔记库集成** | 架构设计已完备 | 尚未编写标准 Obsidian Vault 导出器与 Wikilink 生成逻辑。 |
| **Jupyter Notebook 深度协同** | 存在解析与导出器 | 仅支持 `.ipynb` 的 JSON 结构解析和生成，未在 Web 前端内嵌真实的 JupyterLab 交互内核。 |
| **Model Context Protocol (MCP)** | 在 Backlog 中规划 | 当前所有 28 个工具均运行在本地 FastAPI 进程内的 `ToolRegistry`，无外部 MCP Server 进程。 |
| **纯本地大模型离线网关 (Local LLM)** | 支持通过 OpenAI 兼容 API 指向 Ollama | 代码依赖标准环境变量 `OPENAI_API_BASE` / `LLM_API_KEY`，但前端尚未提供“一键扫描本地 Ollama 模型”的图形化配置向导。 |

---

## 9. 当前技术债务清单 (P0 / P1 / P2)

### 🔴 P0 (直接影响核心功能正确运行)
1. **沙箱受控环境 `__import__` 绑定修复**：
   * **现象**：`RestrictedPythonRunner` 在执行带 `import` 语句的代码时，`safe_builtins_map["__import__"]` 未被 `compile_restricted` 正确识别，导致测试 `test_v24_deep_research.py` 报错 `ImportError: __import__ not found`。
   * **影响**：导致使用默认受控沙箱运行生成的 Python 脚本失败。
   * **修复方向**：在 `backend/domain/data_agent.py` 的沙箱全局命名空间中正确注入 `__import__` 与 `_getitem_` 守卫。

### 🟡 P1 (影响开发体验与前后端闭环完整度)
1. **前端 PDF 划词切片交互与一键 Debugger 弹窗**：
   * 在前端 `LiteraturePanel.vue` 中强化 PDF 结构化浏览与切片一键提取按钮；
   * 在 `WorkspaceMain.vue` 实验代码运行失败时，直接弹出 Debugger 补丁对比与一键重试交互。
2. **测试用例清理与规范化**：
   * 修复 `tests/test_v24_deep_research.py` 的执行断言，确保 `pytest tests/` 100% 全绿。

### 🟢 P2 (长期生态与工程优化)
1. **Obsidian Vault 导出器**：实现将 `Project`、`Hypothesis`、`Paper`、`Evidence`、`Conclusion` 结构化导出为包含 Frontmatter 与 `[[双链]]` 的 Markdown 目录。
2. **轻量化依赖瘦身**：区分可选依赖（如 `pypdf`, `duckdb`）与核心轻量依赖。

---

## 10. 研发演进 Roadmap (Current → Next → Later)

```text
CURRENT (当前正在进行 - V2.4 收敛)
   │
   ├── 1. 修复 RestrictedPython AST 沙箱 import 绑定 (解决 test_v24 P0 断点)
   ├── 2. 前端 LiteraturePanel & Experiment 面板补全 PDF 切片与 Debugger 交互
   └── 3. 运行全量测试套件 (6 个测试套件全 PASS)
   │
   ▼
NEXT (下一阶段核心重点 - V2.5 个人科研工作流拓展)
   │
   ├── 1. Obsidian Markdown / Wikilinks 同步与导出模块 (Vault Adapter)
   ├── 2. PDF.js 本地阅读器组件集成与高亮切片直连
   ├── 3. 本地 Ollama / llama.cpp 一键探测与离线模型自适应
   └── 4. 实验批量超参网格搜索与自动化执行流
   │
   ▼
LATER (远期规划 - V3.0+)
   │
   ├── 1. MCP (Model Context Protocol) 外部插件系统
   ├── 2. PaperQA2 级全文向量混合检索与重排序
   └── 3. 局域网轻量多端同步与只读分享
```

---

## 11. V2.4 Current Focus 与开发检查清单 (Checklist)

### Current Version
* **V2.4.0** (Deep Scientific Productivity Loop)

### Current Phase
* **Phase 14 — 生产力闭环验收完成与产品化收敛 (Productivity Loop Completed)**

### Current Status
* `COMPLETED` (核心功能、沙箱隔离修复、16 步科研用户全流程测试 100% 通过)

### Development Checklist

#### Phase 1: PDF 文献全文解析与证据切片 (P0-A)
- [x] 基于 `pypdf` 实现本地 PDF 页面与章节段落流提取 (`backend/integrations/literature/pdf_reader.py`)
- [x] 实现精确证据切片 `create_paper_evidence_slice` (`Page X · Section Y · Para #Z`)
- [x] 实现基于段落匹配的带引用文献深层问答 (`ask_paper_question`)
- [x] 前端集成 PDF 章节浏览与快速切片 UI (`LiteraturePanel.vue`)

#### Phase 2: 多表 Schema 关联与统计分析向导 (P0-B)
- [x] 自动探测多 Dataset 公共 Join 列并标记 `source="ai_inference"` (`relationship.py`)
- [x] 实现自然语言意图到 SQL / Python 方案的转换 (`wizard.py`)
- [x] 执行分析并一键沉淀为物理 `Artifact`
- [x] 前端 DataAnalysisPanel 接入多表关系与向导 API

#### Phase 3: 实验代码生成、受控运行与智能调试器 (P0-C)
- [x] 基于科研上下文自动合成完整 Python 实验代码 (`generator.py`)
- [x] 智能 Traceback 诊断与修复补丁生成 (`debugger.py`)
- [x] 硬性限制 Debugger 最大 3 次自动重试门禁
- [x] **[P0 Fix]** 修复 RestrictedPython AST 沙箱 `__import__` 绑定问题 (`backend/domain/data_agent.py`)
- [x] 前端 Experiment 详情页嵌入 Debugger 补丁对比与一键重跑面板 (`ProjectDetailView.vue`)

#### Phase 4: 全局审计与全量测试回归
- [x] 注册全部 28 个 Agent 工具并绑定 HITL 权限
- [x] 建立 `docs/RESEARCHOS_DEVELOPMENT_STATUS.md` (SSOT)
- [x] 建立 `docs/CURRENT_STATE.md` 与 `docs/CHANGELOG.md`
- [x] 编写并运行 16 步用户全旅程测试 `tests/test_v24_user_journey.py` (16/16 PASS)
- [x] `pytest tests/` 全部 9 个测试套件 100% 通过 (9/9 PASS)
- [x] 编写 `docs/V2.4_PRODUCT_VALIDATION.md` 作为 V2.5 核心输入文档
