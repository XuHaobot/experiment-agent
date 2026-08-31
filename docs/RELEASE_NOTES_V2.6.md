# ResearchOS V2.6.0 Release Notes (Stable Release)

> **发布版本**：`V2.6.0 (Stable & Feature-Frozen)`  
> **发布日期**：2026-08-31  
> **测试状态**：60/60 PASS (100% 全绿)  
> **定位**：面向科研人员的个人离线科研工作台 (Local-First Personal Research Workspace)

---

## 1. 版本概述

ResearchOS V2.6.0 标志着项目正式完成由“技术原型与多组件实验”向“**真正可用、长期维护、开箱即用**”的科研生产力工具的全面定版与收敛。

本版本重点解决了科研工作流的连续性、可解释性与人机决策体感，消除了伪科学概率数字与黑盒推荐，全面保障科研人员数据隐私与手记安全。

---

## 2. 核心系统能力清单

### 🔬 核心科研空间 (Research Space)
- **Research Question & Hypothesis**：支持提出核心科学问题与 8 态认知状态假说（`ACTIVE`, `SUPPORTED`, `WEAKENED`, `REFUTED`, `TESTING`, `STALE` 等）；
- **Experiment & Runs Tracking**：实验方案与多次运行（Runs）严格层次分立，支持参数字典、多指标（Accuracy, Loss, F1 等）、执行耗时与日志记录；
- **Run Comparison Matrix**：一键横向对比多个 Run 实例，直观呈现自变量变化对指标极值与拐点的影响；
- **Evidence Balance**：正反证据双向记录（Supporting vs Contradicting），严格要求结论基于客观实证；
- **DuckDB & Python Sandbox**：内置 DuckDB 自动解析 CSV/Parquet Schema，结合 RestrictedPython 安全沙箱执行参数敏感度分析。

### 🧭 主动科学探索与防固化 (Active Exploration Engine)
- **多范式候选实验生成**：
  - `Type A (EXPLOIT)`：围绕已知最佳极值进行细粒度微调；
  - `Type B (DISCRIMINATE)`：专门设计用于排除竞争性假说的判决性实验；
  - `Type C (EXPLORE)`：跳跃至未采样的参数空间未知盲区；
  - `Type D (REPLICATE)`：多随机种子复现关键拐点，量化误差条；
- **Hypothesis Discrimination Matrix**：清晰呈现不同实验对各假说的预测分歧；
- **Pseudo-Exploration Detection**：自动检测密集饱和采样区内的无效微调并给出警示；
- **Epistemic Pruning Advisor**：对被多次反驳的假说提出资源倾斜建议，**绝不自动物理删除任何假说**。

### 📔 日常反思与知识互补 (Diary & Obsidian)
- **Research Diary**：记录每日直觉与灵感猜想（`USER_BELIEF` 标记，AI 严禁篡改）；
- **Research Session**：轻量记录单轮工作跨文献、数据、假说与结论的操作足迹；
- **Obsidian Vault Bridge**：双向导出 Markdown、YAML Frontmatter 与 `[[Wikilinks]]`，独创 `<!-- RESEARCHOS:START -->` 段落隔离技术，100% 保护 Obsidian 中的个人手记。

### 🛡️ 本地 AI 与隐私门禁 (Local AI & Privacy Gateway)
- **Local Ollama 驱动**：本地模型直接运行，数据 100% 留存本机；
- **4 级数据分类 & 3 级门禁**：自动识别 `PUBLIC`, `INTERNAL`, `SENSITIVE`, `RESTRICTED`，敏感信息非授权绝不发送到外部。

---

## 3. 测试与工程质量

```text
============================= test session starts =============================
platform win32 -- Python 3.12.0
collected 60 items

tests/test_v21_research_workflow.py (1 test) PASSED       [  1%]
tests/test_v22_open_research_stack.py (5 tests) PASSED    [ 10%]
tests/test_v23_research_closure.py (1 test) PASSED        [ 11%]
tests/test_v24_deep_research.py (1 test) PASSED           [ 13%]
tests/test_v24_user_journey.py (16 steps) PASSED          [ 15%]
tests/test_v25_phase15.py (9 tests) PASSED                [ 30%]
tests/test_v25_phase16_vault.py (10 tests) PASSED         [ 46%]
tests/test_v25_phase17_memory.py (14 tests) PASSED        [ 70%]
tests/test_v25_phase18_exploration.py (17 tests) PASSED   [ 98%]
tests/test_v26_product_workflow.py (1 test) PASSED        [100%]

======================= 60 passed, 3 warnings in 39.58s =======================
```

---

## 4. 后续演进原则

本版本已执行 **Feature Freeze（功能冻结）**。后续的小版本（V2.6.x）将完全由真实科研人员的使用痛点和需求驱动，优先进行使用流畅度优化与 Bug 修复。
