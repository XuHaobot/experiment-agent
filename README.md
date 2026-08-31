# ResearchOS (Experiment Agent) 🔬

> **AI-Agnostic, Local-First 个人科研操作系统与实验智能体工作台**  
> *无缝连接外部 AI (Codex / Claude Code / ChatGPT)、实验室 GPU (4090 / 集群)、文献研读、假说演进、多 Run 对比、实证天平、主动探索、科研日记与 Obsidian 知识库。*

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

## 📖 项目愿景与设计哲学

在传统科研工作流中，论文研读、数据统计、代码实现、超参记录和结论复盘往往割裂在不同的工具中（Zotero、Jupyter、终端日志、微信/GPT 对话框）。

**ResearchOS** 是一个面向科研人员长期使用的 **AI-Agnostic（AI 无关）个人科研中控工作台**。它不试图替代您的外部 AI（OpenAI Codex、Claude Code、ChatGPT）或计算硬件（本地 RTX 4090、学校超算集群），而是作为您的**核心因果记忆与实验中枢**：

```text
科研人员 (直觉与文献)
   │
   ├── 外部大模型 (Codex / Claude Code / ChatGPT / DeepSeek / 本地 Ollama)
   │       │
   │       ├── 编写 PyTorch / JAX 训练脚本
   │       ├── 在 GPU 服务器上执行模型训练
   │       └── 输出终端日志、CSV 指标与权重 Checkpoint
   │
   └── ResearchOS (核心证据天平与科研工作台)
          │
          ├── 1. Research Question (核心科学问题管理)
          ├── 2. 8态假说生命周期 (Active, Supported, Weakened, Refuted...)
          ├── 3. 实验方案与多 Run 运行 (解耦方案与参数遥测记录)
          ├── 4. ⚡ Quick Capture (30 秒科研会话与操作快速沉淀)
          ├── 5. 📊 多 Run 横向对比矩阵 (自动对齐参数并标出 👑 最优拐点)
          ├── 6. 正反证据天平 (Supporting vs Contradicting Balance)
          ├── 7. 客观实证结论 (严格锚定 Run ID 与文献引用，杜绝幻觉)
          ├── 8. 🧭 主动科学探索引擎 (Type A/B/C/D 候选组合与假说判决矩阵)
          ├── 9. 📔 Research Diary (USER_BELIEF 每日手记，AI 禁改)
          ├── 10. 📚 Obsidian Vault Bridge (双向导出与手记段落隔离保护)
          └── 11. 外部大模型学术提示词桥梁 (一键导出高质量 Context Prompt 给 Codex)
```

---

## ✨ 核心能力与功能特性 (V2.5 & V2.6 全量实装)

### 1. ⚡ 30 秒科研快速沉淀与外部执行 (Quick Capture & External AI Workflow)
- **30 秒极速记录 (Quick Capture)**：顶栏一键唤起轻量弹窗，记录做了什么、使用了什么工具（Codex / Claude Code / 手工等）、实验结果、意外反思与下一步计划。
- **外部运行执行来源 (`execution_origin`)**：原生支持 `LOCAL_SANDBOX`, `CODEX`, `CLAUDE_CODE`, `EXTERNAL_LOCAL`, `REMOTE_SERVER`, `MANUAL`, `IMPORTED`。
- **Git Commit 溯源**：单次运行原生绑定 `git_commit`、`git_branch` 与 `repository`。
- **外部大模型提示词桥梁 (Prompt Bridge)**：一键打包当前假说、历史最优运行参数、失败教训与未探索盲区，直接复制并粘贴给 ChatGPT / Codex。

### 2. 📊 多 Run 横向对比矩阵与 CSV 批量导入 (Run Comparison & CSV Ingestion)
- **外部 CSV 一键导入**：将外部自动化训练产生的指标表格拖拽导入，自动推断列类型并批量创建 `ExperimentRun`。
- **多 Run 横向对比矩阵 (`compare_runs`)**：勾选多个运行实例，横向对齐所有自变量输入与因变量指标，高亮标出最优表现（👑 BEST）与极值拐点坐标。

### 3. 🔬 8 态假说生命周期与正反证据天平 (8-Tier Hypothesis & Evidence Balance)
- **假说状态机**：假说在 `ACTIVE`（活跃中）、`SUPPORTED`（充分支撑）、`WEAKENED`（被削弱）、`REFUTED`（被否定）、`TESTING`（测试中）、`STALE`（停滞）等 8 态间流转。
- **正反证据天平 (Evidence Balance)**：实时统计 Supporting（正向支持）与 Contradicting（反面矛盾）比例，主动防范确认偏误 (Confirmation Bias)。
- **严谨证据支撑的结论 (Conclusions)**：结论强制关联具体 Run ID 或文献切片，严禁凭空生成结论。

### 4. 🧭 主动科学探索引擎与假说判决 (Active Exploration & Epistemic Pruning)
- **多范式候选实验组合**：
  - `Type A (EXPLOIT · 极值精调)`：围绕已知最佳参数微调锁定极值；
  - `Type B (DISCRIMINATE · 假说判决)`：设计解耦实验区分相互竞争的理论解释；
  - `Type C (EXPLORE · 盲区探测)`：跳跃探测未采样的参数未知盲区；
  - `Type D (REPLICATE · 稳定性复现)`：变换随机种子量化误差条与复现性。
- **假说区分度矩阵 (Discrimination Matrix)**：直观对比每个实验在不同假说下的理论预测差异。
- **伪探索警示**：自动检测密集饱和区间内的无效微调并报警。
- **非破坏性假说修剪顾问**：建议调低被否定假说的资源预算，**绝对不自动物理删除任何假说**。

### 5. 📔 科研日记与日常手记 (Research Diary & Sessions)
- **Research Diary**：为科研人员提供随手记录直觉灵感与观察的专属手记，标记为 `USER_BELIEF`（AI 绝无权限篡改或伪造）。
- **Research Session**：轻量记录一轮连续工作的跨模块足迹（查看文献、执行 Runs、沉淀结论）。

### 6. 📚 Obsidian 知识库双向投影 (Obsidian Vault Bridge)
- **双向导出**：一键导出为 Obsidian 标准格式（`01_Projects`, `02_Hypotheses`, `03_Experiments`, `05_Conclusions` 等），带 YAML Frontmatter 与 `[[Wikilinks]]`。
- **100% 笔记段落保护**：采用 `<!-- RESEARCHOS:START -->` 标记隔离，您在 Obsidian 中手写撰写的个人笔记在重新同步时永不覆盖。

### 7. 🛡️ 本地 AI、三级隐私门禁与零模型降级 (Local AI & Privacy Gateway)
- **零 LLM 优雅降级 (Zero-LLM Fallback)**：即使在不配置任何模型、离线断网环境下，全部台账管理、多 Run 对比、DuckDB 数据分析与 Obsidian 导出 100% 正常运行。
- **本地 Ollama 与云端 BYOK**：支持本地 Ollama（如 `qwen2.5-coder`），也支持配置 DeepSeek / OpenAI API Key（0 显存占用，4090 显存 100% 留给训练）。
- **三级隐私门禁**：自动识别 `PUBLIC` / `INTERNAL` / `SENSITIVE` / `RESTRICTED`，敏感信息非授权绝不发送到外部。

### 8. 📖 系统内置交互式使用指南中心 (In-App User Guide)
- 顶栏一键唤起 `UserGuideModal`，内置 9 大交互章节与可复制的 Python API 集成代码。

---

## 🚀 快速开始

### 1. 环境要求
- **Python**: 3.10, 3.11 或 3.12
- **Node.js**: 18.0 或更高版本 (用于前端构建)
- **OS**: Windows / macOS / Linux

### 2. Windows 一键启动
双击根目录脚本：
```cmd
start.bat
```
脚本将自动启动：
* **FastAPI 后端服务**：`http://127.0.0.1:5001` (交互式 API 文档: `http://127.0.0.1:5001/docs`)
* **Vue3 前端工作台**：`http://localhost:3000`

### 3. 手动分步启动
```bash
# 1. 克隆代码库
git clone https://github.com/XuHaobot/experiment-agent.git
cd experiment-agent

# 2. 安装 Python 虚拟环境与依赖
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# 3. 启动后端
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5001 --reload

# 4. 启动前端 (另开终端)
cd frontend
npm install
npm run dev
```

---

## ⚡ REST API 与 Python 训练代码集成示例

ResearchOS 提供完备的 RESTful API，可直接与 PyTorch 训练代码、Jupyter Notebook 或外部脚本联动：

```python
import requests

BASE = "http://127.0.0.1:5001"

# 1. 记录单次实验运行 (带 Git Commit 与外部 Codex 来源)
run_res = requests.post(f"{BASE}/api/runs", json={
    "experiment_id": "exp_k_sweep",
    "actual_parameters": {"k": 25, "lr": 1e-4, "residual": True},
    "metrics": {"val_accuracy": 0.912, "loss": 0.098},
    "status": "completed",
    "execution_origin": "CODEX",
    "git_commit": "a82f31c",
    "ai_tool_used": "Codex"
}).json()
print("Recorded Run ID:", run_res["id"])

# 2. 横向多 Run 参数与指标矩阵比对
comp_res = requests.post(f"{BASE}/api/runs/compare", json={
    "run_ids": ["run_01", "run_02", run_res["id"]]
}).json()
print("Optimal Run:", comp_res["best_run_id"])
print("Insights:", comp_res["insights"])

# 3. 30 秒快速记录科研会话 (Quick Capture)
qc_res = requests.post(f"{BASE}/api/projects/proj_01/quick-capture", json={
    "title": "残差连接过平滑解耦验证",
    "what_i_did": "使用 Codex 修改聚合层为 Initial Residual Mapping",
    "what_happened": "准确率在 k=25 达到 91.2%",
    "ai_tool_used": "Codex",
    "git_commit": "a82f31c"
}).json()

# 4. 获取供外部 Codex / ChatGPT 使用的结构化 Prompt
prompt_res = requests.get(f"{BASE}/api/projects/proj_01/external-prompt").json()
print("Copy this to Codex:\n", prompt_res["prompt_text"])
```

---

## 🧪 全量自动化测试套件 (61/61 PASS)

本项目具备覆盖完整科研闭环的 61 个自动化测试用例，涵盖 V2.1 至 V2.6 所有功能：

```bash
pytest tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.0
collected 61 items

tests/test_v21_research_workflow.py (1 test) PASSED       [  1%]  # V2.1 领域模型与记忆问答
tests/test_v22_open_research_stack.py (5 tests) PASSED    [  9%]  # V2.2 开源学术栈 (OpenAlex/arXiv/DuckDB/Jupyter)
tests/test_v23_research_closure.py (1 test) PASSED        [ 11%]  # V2.3 真实科研闭环穿透与双向因果溯源
tests/test_v24_deep_research.py (1 test) PASSED           [ 13%]  # V2.4 深度研读、向导与代码调试器
tests/test_v24_user_journey.py (16 steps) PASSED          [ 14%]  # V2.4 科研人员 16 步旅程
tests/test_v25_phase15.py (9 tests) PASSED                [ 29%]  # V2.5 Phase 15 本地 AI 与隐私门禁
tests/test_v25_phase16_vault.py (10 tests) PASSED         [ 45%]  # V2.5 Phase 16 Obsidian Vault 网桥
tests/test_v25_phase17_memory.py (14 tests) PASSED        [ 68%]  # V2.5 Phase 17 科研记忆 2.0 与防固化
tests/test_v25_phase18_exploration.py (17 tests) PASSED   [ 96%]  # V2.5 Phase 18 主动探索引擎与判决矩阵
tests/test_v26_product_workflow.py (1 test) PASSED        [ 98%]  # V2.6 20 步科研工作流连续性测试
tests/test_v26_real_research_workflow.py (1 test) PASSED  [100%]  # V2.6 AI-Agnostic 与真实科研人员全流程测试

======================= 61 passed, 3 warnings in 50.36s =======================
```

---

## 📂 核心代码架构

```text
experiment-agent/
├── backend/
│   ├── domain/                # 核心领域实体与业务逻辑
│   │   ├── project.py         # 课题与核心问题
│   │   ├── hypothesis.py      # 8 态科学假说状态机
│   │   ├── run.py             # 实验运行、CSV 导入与多 Run 对比
│   │   ├── session.py         # 快速记录 (Quick Capture) 与 Prompt 桥梁
│   │   ├── exploration.py     # 主动探索 (Type A/B/C/D) 与假说判决矩阵
│   │   ├── diary.py           # 科研日记手记 (USER_BELIEF)
│   │   ├── timeline.py        # 全景科研演进时间线
│   │   ├── dataset.py         # DuckDB Schema 推断与 SQL 分析
│   │   ├── artifact.py        # SHA256 去重科研资产与血缘
│   │   └── conclusion.py      # 实证支撑科学结论
│   ├── vault/                 # Obsidian Vault Bridge 子系统
│   ├── security/              # 4 级数据分类与 3 级隐私门禁
│   ├── llm/                   # 本地 Ollama 驱动与 OpenAI/DeepSeek 网关
│   └── main.py                # FastAPI 路由与入口
├── frontend/                  # Vue3 个人科研工作台
│   ├── src/
│   │   ├── components/        # QuickCapture, UserGuide, Explore, Compare, Diary
│   │   └── views/             # ProjectDetailView.vue 课题工作区
│   └── dist/                  # 前端静态生产构建产物
├── data/                      # Local-First 本地存储
├── docs/                      # 核心规范与使用手册
│   ├── RESEARCHOS_FINAL_STATUS.md # SSOT 最终产品定版报告
│   ├── USER_AND_API_GUIDE.md  # 全模块使用与 API 接入开发手册
│   └── RELEASE_NOTES_V2.6.md  # V2.6.0 正式发布日志
├── tests/                     # 61 个自动化回归测试用例
└── start.bat                  # Windows 一键启动脚本
```

---

## 📜 核心文档索引

* [**全量使用与 API 手册**](docs/USER_AND_API_GUIDE.md)：涵盖每个面板的交互使用与完整 REST API 接入规范。
* [**最终定版报告**](docs/RESEARCHOS_FINAL_STATUS.md)：系统设计决策与功能冻结声明。
* [**版本发布说明**](docs/RELEASE_NOTES_V2.6.md)：V2.6.0 详细更新日志。

---

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。
