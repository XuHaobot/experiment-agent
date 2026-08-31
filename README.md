# ResearchOS (Experiment Agent) 🔬

> **AI-Native Local-First 个人科研操作系统与实验智能体工作台**  
> *从文献研读、证据沉淀、假说建立，到数据分析、实验编程、运行调试与结论推演的全闭环科研平台。*

[**中文文档**](README.md) | [**English Documentation**](README_EN.md)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vuedotjs)](https://vuejs.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Local%20Analytics-FFF000?logo=duckdb)](https://duckdb.org/)
[![RestrictedPython](https://img.shields.io/badge/RestrictedPython-Safe%20Sandbox-green)](https://restrictedpython.readthedocs.io/)
[![Status](https://img.shields.io/badge/Status-V2.6.0%20Stable-brightgreen)](docs/RELEASE_NOTES_V2.6.md)
[![Tests](https://img.shields.io/badge/Tests-61%2F61%20PASS-success)](tests/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 项目愿景

传统科研工作流中，论文研读、数据统计、代码实现、超参记录和结论复盘往往割裂在不同的工具中（Zotero、Jupyter、终端日志、微信/GPT 对话框）。

**ResearchOS** 是一个面向科研人员长期使用的 **AI 原生科研工作台**。它遵循 **Local-First** 单机轻量原则，拒绝虚构数据与大模型幻觉，通过严格的**数据血缘（Lineage）与因果溯源（Causal Graph）**，将零散的科研资产串联成真实可验证的闭环：

```
                    ┌─────────────────────────┐
                    │  1. 科学文献 (Literature) │ (OpenAlex / arXiv / S2 / 本地 PDF)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  2. 证据切片 (Evidence)  │ (Page X · Section Y · Para #Z)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  3. 科学假说 (Hypothesis)│ (Testing / Supported / Refuted)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  4. 实验方案 (Experiment)│ (Protocol & Parameter Space)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  5. 数据集 (Dataset)     │ (DuckDB / SQLite / CSV 真实分析)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  6. 物理执行 (Run)      │ (RestrictedPython / Jupyter / MLflow)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  7. 科研产物 (Artifact) │ (Charts / Notebooks / Data Reports)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  8. 沉淀结论 (Conclusion)│ (锚定 Evidence 强支撑，无幻觉)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  9. 下一步行动 (Next)   │ (AI 推演高信息增益实验 + HITL 审批)
                    └─────────────────────────┘
```

---

## ✨ 核心能力与功能特性

### 1. 📚 文献深度研读与 PDF 证据切片 (P0-A)
- **多源开放检索**：一键跨库搜索 OpenAlex、arXiv、Semantic Scholar 官方学术元数据。
- **本地 PDF 解析**：轻量解析 PDF 页面、章节（`Abstract`、`Method`、`Experiments` 等）与段落流。
- **精确证据切片**：支持直接从 PDF 段落中抽取科研依据，标记 `Page X · Section Y · Para #Z` 并沉淀为 Evidence。
- **Grounded 文献问答**：对论文原文进行针对性问答，回答强制附带页码与章节引用。

### 2. 📊 多数据表关联与统计分析向导 (P0-B)
- **自动 Schema 理解**：自动比对多个 Dataset 的列名，推断潜在主外键关联（标记 `source="ai_inference"`）。
- **DuckDB 极速分析**：本地高效执行真实 SQL 聚合与多表 JOIN，支持自动 SQLite 内存引擎 fallback。
- **统计分析向导 (Wizard)**：输入自然语言意图（如“比较 A/B 两组均值差异”），自动生成对应 SQL 与 Python 分析方案并一键归档为 Artifact 产物。

### 3. 💻 实验方案代码生成与一键调试器 (P0-C)
- **科研上下文代码合成**：自动读取 Project、Hypothesis、Experiment 方案与 Dataset Schema，生成规范的 Python 实验脚本。
- **安全沙箱受控执行**：在 RestrictedPython 隔离环境中执行，内置 `numpy`、`pandas`、`scipy`、`matplotlib`，捕获遥测指标与图表。
- **智能诊断与一键修复**：遇到运行期异常（如 `KeyError`、`ZeroDivisionError`）时，Agent 自动诊断根因并生成补丁（严格受限于最大 3 次自动重试门禁）。

### 4. 🧠 科研记忆与零幻觉问答 (Research Memory)
- **事实分级体系**：所有科研解答严格分为 `SUPPORTED`（有实验证据）、`PARTIALLY_SUPPORTED`（文献或部分推理）与 `UNSUPPORTED`（无依据）。
- **严禁虚构事实**：在没有实验 Run 或 Evidence 时，明确拒绝将推测宣称为已证明。
- **双向因果图谱溯源**：点击任意 Conclusion，可反向多跳追溯至 `Conclusion → Evidence → Artifact/Run → Dataset/Experiment → Hypothesis → Paper → Project`。

### 5. 🛡️ ToolRegistry 与人机协同门禁 (HITL)
- **全局注册 28 个科研工具**：涵盖文献检索、PDF 解析、SQL 查询、代码生成与沙箱执行。
- **严格权限与风控分级**：高风险操作（`execute_run`、`run_experiment`）强制进入 HITL 审批工单流，人工二次确认后方可执行。

---

## 🖥️ 界面概览 (Scientific IDE)

- **Research Cockpit (科研驾驶舱)**：实时追踪核心科学问题、假说覆盖率、最佳运行指标与不确定性状态。
- **Timeline (演进时间线)**：按时序追踪假说提出、数据导入、分析执行与结论沉淀。
- **Causal Graph (因果图谱)**：全景可视化论文、数据、实验、产物与结论的双向拓扑血缘。
- **Literature & PDF Reader (文献工作台)**：在线学术检索、PDF 章节阅读与切片提取。
- **Data Workbench (数据分析台)**：Python 沙箱、参数敏感度分析与交互式分析向导。
- **Experiment & Coder (实验编程台)**：实验方案管理、代码一键生成、沙箱运行与智能调试器。

---

## 🚀 快速开始

### 1. 环境要求
- **Python**: 3.10 或更高版本
- **Node.js**: 18.0 或更高版本 (用于前端构建)
- **OS**: Windows / macOS / Linux

### 2. 后端安装与配置
克隆仓库并创建虚拟环境：
```bash
git clone https://github.com/XuHaobot/experiment-agent.git
cd experiment-agent

# 创建并激活虚拟环境
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

配置大语言模型（可选，支持任何 OpenAI 兼容 API）：
```bash
# 复制环境变量模板
cp .env.example .env
```
在 `.env` 中填写你的配置（未配置时系统将自动启用 Local-First 确定性引擎）：
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

### 3. 前端编译
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. 启动服务
```bash
# 启动 FastAPI 后端与 Web IDE
python backend/main.py
```
打开浏览器访问：`http://localhost:5001`

---

## 🧪 自动化测试套件

本项目具备覆盖完整科研闭环的自动化测试验证体系：

```bash
# 1. V2.4 深度科研生产力测试 (PDF研读、向导、代码生成与调试器)
python tests/test_v24_deep_research.py

# 2. V2.3 真实科研闭环穿透测试 (14 项全流程验证)
python tests/test_v23_research_closure.py

# 3. V2.2 开放学术生态集成测试 (OpenAlex / arXiv / DuckDB / Jupyter)
python tests/test_v22_open_research_stack.py

# 4. V2.1 真实科研工作流测试 (因果图谱溯源与记忆问答)
python tests/test_v21_research_workflow.py

# 5. P0 架构级验收测试 (ToolRegistry、权限与 HITL 门禁)
python tests/test_p0_acceptance.py
```

---

## 📂 项目目录结构

```text
experiment-agent/
├── backend/
│   ├── agent/                 # Agent 核心、ToolRegistry (28工具) 与 HITL 安全门禁
│   │   ├── security/          # 权限分级与审批流 (guard.py, permission.py)
│   │   └── tools/             # 工具注册中心 (registry.py)
│   ├── domain/                # 领域模型与核心业务 (Local-First 零外部依赖)
│   │   ├── project.py         # 课题与科学问题
│   │   ├── paper.py           # 文献实体与 PDF 证据切片
│   │   ├── hypothesis.py      # 科学假说生命周期
│   │   ├── experiment.py      # 实验方案设计
│   │   ├── dataset.py         # 数据集管理与统计概览
│   │   ├── run.py             # 物理运行实例与遥测数据
│   │   ├── artifact.py        # 科研产物 (图表/报告/Notebook)
│   │   ├── conclusion.py      # 证据锚定的科研结论
│   │   ├── memory.py          # 科研记忆与事实问答 (Grounding)
│   │   └── experiment_coder.py# 实验代码生成与调试领域服务
│   ├── integrations/          # 外部开源生态适配器 (Adapters)
│   │   ├── literature/        # OpenAlex / arXiv / S2 / PDF Reader
│   │   ├── data/              # DuckDB / SQLite SQL 引擎与分析向导
│   │   ├── notebook/          # Jupyter .ipynb 解析与导入
│   │   ├── experiment/        # MLflow 本地指标同步
│   │   └── execution/         # RestrictedPython / DockerRunner 代码执行与调试
│   └── main.py                # FastAPI 入口与 RESTful 路由
├── frontend/                  # Vue3 Scientific IDE 前端工程
│   ├── src/
│   │   ├── components/        # 核心面板 (Literature, Analysis, Artifact, Conclusion)
│   │   └── views/             # ProjectDetailView.vue 全局科研工作台
│   └── dist/                  # 前端静态生产构建产物
├── data/                      # Local-First 物理持久化数据存储目录
│   ├── projects/              # 项目元数据
│   ├── papers/                # 保存的文献与 PDF 结构化解析
│   ├── datasets/              # 本地真实 CSV / Parquet
│   ├── runs/                  # 运行实例遥测记录
│   ├── artifacts/             # 沉淀的图表与分析报告
│   └── conclusions/           # 经过验证的科研结论
├── tests/                     # 自动化端到端测试套件
└── docs/                      # 架构设计与闭环审计验收报告
```

---

## 📜 开源协议

本项目基于 [MIT License](LICENSE) 开源。欢迎学术界与工业界科研同行共同交流与共建！
