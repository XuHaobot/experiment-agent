# ResearchOS Final Product Status Report (V2.6.0 Stable / Product-Frozen)

> **最终定版状态**：`V2.6.0 (STABLE / PRODUCT-FROZEN)`  
> **文档性质**：Single Source of Truth (SSOT) 最终产品收敛归档  
> **发布日期**：2026-08-31  
> **自动化测试**：61/61 PASS (100% 全绿通过)

---

## 1. 当前最终版本
* **版本号**：`ResearchOS V2.6.0`
* **生命周期状态**：**STABLE / PRODUCT-FROZEN**（正式稳定定版，全面停止主动增加大型框架功能，后续仅接受真实科研用户反馈驱动的微小修复与优化）。

---

## 2. 产品定位 (Product Definition)
> **ResearchOS 是一个面向科研人员的个人离线科研工作台 (Local-First Personal Research Workspace)。**  
> 它不负责替科研人员做完所有科研，而负责让科研人员在使用 Codex、Claude Code、ChatGPT、Python、GPU 训练和自己的学术经验完成科研后，**所有重要过程都能留下可追溯、可复现、可继续的严谨科研记忆**。

```text
科研人员
   │
   ├── 想法 / 灵感
   │
   ├── 文献 (OpenAlex / arXiv / S2 / 本地 PDF 切片)
   │
   ├── 外部大模型 (Codex / Claude Code / Gemini / ChatGPT / 本地 Ollama)
   │       │
   │       ├── 编写实验代码
   │       ├── 运行模型训练 (本地 4090 / 学校集群 / 远程服务器)
   │       └── 分析报错与输出
   │
   └── ResearchOS (中枢记录与推演层)
          │
          ├── Research Question (科学问题)
          ├── Hypothesis (8 态科研假说状态机)
          ├── Experiment & Runs (参数/指标/CSV 批量导入/横向对比)
          ├── Quick Capture (30 秒科研工作快速沉淀)
          ├── Evidence Ledger (正反证据天平)
          ├── Conclusion (实证支撑结论)
          ├── Research Diary (USER_BELIEF 每日手记)
          ├── Research Timeline (科研因果演进时间线)
          ├── Active Exploration (Type A/B/C/D 候选实验组合与假说判决矩阵)
          └── Obsidian Vault Bridge (双向 Markdown 导出与手记段落隔离保护)
```

---

## 3. 已实现核心能力清单
1. **科研空间管理**：Project（课题）、Research Question（科学问题）、Hypothesis（8 态认知假说状态机）；
2. **多源文献与精准切片**：OpenAlex/arXiv/S2 学术文献检索，本地 PDF 章节与页码切片（`Page X · Sec Y`）；
3. **实验方案与多 Run 追踪**：方案与运行解耦，记录参数字典、指标（Accuracy, Loss, F1 等）、执行耗时与日志；
4. **外部 CSV 批量导入**：支持将外部自动化训练产生的 CSV 结果一键批量转化为多个 Run；
5. **多 Run 横向对比矩阵 (`compare_runs`)**：自动横向对齐多组自变量与指标，高亮显示最优运行（👑 BEST）与极值拐点；
6. **DuckDB 结构化分析与受控沙箱**：内置 DuckDB SQL 查询，结合 RestrictedPython 安全沙箱执行敏感度分析并生成 Artifacts（附带 SHA256 与血缘）；
7. **正反证据天平 (Evidence Balance)**：实时计算 Supporting / Contradicting / Unknown 分布，主动对抗确认偏误；
8. **客观实证结论 (Conclusions)**：强制要求结论关联具体 Run ID 或文献切片，杜绝凭空生成虚假结论；
9. **主动科学探索引擎 (Active Exploration)**：
   - `Type A (EXPLOIT · 极值精调)`
   - `Type B (DISCRIMINATE · 假说判决)`
   - `Type C (EXPLORE · 盲区探测)`
   - `Type D (REPLICATE · 稳定性复现)`
   - 假说区分度矩阵 (Discrimination Matrix)
   - 伪探索饱和区间警示 (Pseudo-Exploration Detector)
   - 非破坏性假说修剪顾问 (Epistemic Pruning Advisor)
   - HITL 人工批准门禁 (Approve $\to$ 生成新实验草稿)；
10. **科研快速记录 (Quick Capture)**：30 秒记录本次做了什么、使用了什么外部 AI 工具、实验结果与反思；
11. **外部大模型提示词桥梁 (Prompt Bridge)**：一键打包当前假说、最优参数、失败教训与探索目标为学术 Prompt，直接粘贴给 Codex / ChatGPT；
12. **科研手记与会话**：`Research Diary`（标记 `USER_BELIEF`，AI 禁改）与 `Research Session`（轻量记录工作足迹）；
13. **Obsidian Vault 网桥**：双向导出 Markdown 笔记与 Wikilinks，采用 `<!-- RESEARCHOS:START -->` 100% 保护用户手写笔记；
14. **本地 AI 与三级隐私门禁**：支持本地 Ollama，支持 OpenAI/DeepSeek 兼容 API（BYOK 模式，0 显存占用），具备 4 级数据分类与 3 级隐私门禁（`ALLOW`/`ASK`/`DENY`）；
15. **系统内置指南中心**：顶栏一键唤起 `UserGuideModal`，内置 9 大交互章节与可复制 Python 接入代码。

---

## 4. 明确不实现的能力清单 (Explicit Non-Goals)
* ❌ **不实现无人值守自动实验机器人**（实验必须由科研人员确认或外部执行）；
* ❌ **不实现多 Agent 自由对话网络 / 插件市场**（杜绝不可控的幻觉与系统臃肿）；
* ❌ **不引入 Kubernetes / Slurm / 分布式算力调度**（保持轻量 Local-First）；
* ❌ **不引入外置向量数据库 / PostgreSQL / Docker 强制依赖**（采用轻量 SQLite / DuckDB / JSON 存储）；
* ❌ **不自动修改科研人员假说或强制删除假说**（假说修剪仅提供参考，绝不自动物理删除）。

---

## 5. 核心数据模型 (Data Models)
* **`Project`**：`id`, `name`, `description`, `questions`, `experiment_ids`, `created_at`
* **`Hypothesis`**：`id`, `project_id`, `question_id`, `title`, `description`, `status` (`ACTIVE`/`SUPPORTED`/`WEAKENED`/`REFUTED`/`TESTING`/`STALE`), `evidence`
* **`ExperimentRecord`**：`id`, `task`, `params`, `project_id`, `status` (`draft`/`completed`)
* **`ExperimentRun`**：`id`, `experiment_id`, `actual_parameters`, `metrics`, `logs`, `artifacts`, `status`, `execution_origin` (`LOCAL_SANDBOX`/`EXTERNAL_LOCAL`/`REMOTE_SERVER`/`CODEX`/`CLAUDE_CODE`/`MANUAL`/`IMPORTED`), `git_commit`, `git_branch`, `repository`, `ai_tool_used`
* **`ResearchSession`**：`id`, `project_id`, `title`, `what_i_did`, `tools_used`, `what_happened`, `what_surprised_me`, `current_belief`, `next_step`, `ai_tool_used`, `git_commit`
* **`ResearchDiary`**：`id`, `project_id`, `date`, `title`, `content`, `tags`, `epistemic_status` (`USER_BELIEF`)
* **`Evidence`**：`id`, `source` (`run_id` / `paper_id` / `artifact_id`), `text`, `supports` (bool), `epistemic_status` (`OBSERVATION`/`FACT`)
* **`Conclusion`**：`id`, `project_id`, `hypothesis_id`, `text`, `confidence` (`high`/`medium`/`low`), `evidence_refs`

---

## 6. AI-Agnostic 架构与 Provider 适配
系统在产品层面实现了 **AI-Agnostic（AI 无关性）**：
* **零 AI 模式 (No AI)**：不配置任何 API Key 或模型，所有核心功能（假说、多 Run 对比、DuckDB 分析、证据天平、Obsidian 导出）100% 完整可用；
* **本地 AI 模式 (Local Ollama)**：连接本地 `ollama serve`，数据 100% 离线，0 数据外泄；
* **云端 API 模式 (BYOK: DeepSeek / OpenAI / Claude)**：仅需在设置中填入 API Key，单张 4090 显存 **0 占用**，调用轻量迅速。

---

## 7. 隐私与数据安全门禁 (Privacy Boundary)
* 4 级分类：`PUBLIC`（公开论文元数据）、`INTERNAL`（项目 ID/键名）、`SENSITIVE`（未公开参数/路径）、`RESTRICTED`（API Keys/敏感密钥）；
* 3 级门禁：`ALLOW`（放行）、`ASK`（需用户确认）、`DENY`（硬拦截）；
* 严格审计：所有隐私决策透明保存于 `data/audit/privacy_audit.jsonl`。

---

## 8. Obsidian Vault 知识库深度集成
* 标准目录输出：`01_Projects`, `02_Hypotheses`, `03_Experiments`, `05_Conclusions`；
* 独创段落隔离技术：`<!-- RESEARCHOS:START -->` 标记由系统管理，用户在标记外手写的 Markdown 思考笔记在重新同步时永远得到保护。

---

## 9. 自动化测试结果 (Test Suite Report)
```text
============================= test session starts =============================
platform win32 -- Python 3.12.0
collected 61 items

tests/test_v21_research_workflow.py (1 test) PASSED       [  1%]
tests/test_v22_open_research_stack.py (5 tests) PASSED    [  9%]
tests/test_v23_research_closure.py (1 test) PASSED        [ 11%]
tests/test_v24_deep_research.py (1 test) PASSED           [ 13%]
tests/test_v24_user_journey.py (16 steps) PASSED          [ 14%]
tests/test_v25_phase15.py (9 tests) PASSED                [ 29%]
tests/test_v25_phase16_vault.py (10 tests) PASSED         [ 45%]
tests/test_v25_phase17_memory.py (14 tests) PASSED        [ 68%]
tests/test_v25_phase18_exploration.py (17 tests) PASSED   [ 96%]
tests/test_v26_product_workflow.py (1 test) PASSED        [ 98%]
tests/test_v26_real_research_workflow.py (1 test) PASSED  [100%]

======================= 61 passed, 3 warnings in 50.36s =======================
```

---

## 10. 部署与启动方式
* **一键启动**：双击根目录 [`start.bat`](file:///e:/textool/experiment-agent/start.bat) 即可自动拉起后端（`127.0.0.1:5001`）与前端（`localhost:3000`）；
* **手动启动**：
  ```bash
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 5001 --reload
  cd frontend && npm run dev
  ```

---

## 11. 最终收敛原则与后续演进机制

> **V2.6 是 ResearchOS 的最终功能收敛版本。**  
> 从此刻起，系统进入 **Feature-Frozen（功能冻结）** 维护阶段。  
> 坚决不再进行为了“增加功能数量”的主动开发。后续的一切演进将严格遵循：
> 
> $$\text{真实用户使用反馈} \longrightarrow \text{问题复现} \longrightarrow \text{极简针对性修复} \longrightarrow \text{回归测试}$$
