# ResearchOS Current State (Single Source of Truth)

> **Quick Snapshot for Developers & Researchers**  
> *Final Stabilization & Feature-Frozen State.*

---

## 1. Version & Phase
- **Current Version**: `V2.6.0 (Stable Release)`
- **Current Phase**: `AI-Agnostic Research Workflow & Final Stabilization (COMPLETED)`
- **Overall Status**: `STABLE / PRODUCT-FROZEN / 61 TESTS PASS / READY FOR PRODUCTION USE`
- **Last Updated**: 2026-08-31

---

## 2. Completed Capabilities (V2.6 Final Delivery)
- **AI-Agnostic Research Workflow**:
  - `backend/domain/run.py`: 扩展 `execution_origin` (`LOCAL_SANDBOX`, `EXTERNAL_LOCAL`, `REMOTE_SERVER`, `CODEX`, `CLAUDE_CODE`, `MANUAL`, `IMPORTED`)，绑定 `git_commit`, `git_branch`, `repository`, `ai_tool_used`。
  - `backend/domain/session.py`: 支持 `Quick Capture` 快速记录（`what_i_did`, `tools_used`, `what_happened`, `what_surprised_me`, `current_belief`, `next_step`）与外部大模型提示词桥梁 (`generate_external_prompt`)。
  - `backend/domain/timeline.py`: 将 Research Sessions、Git Commits、Papers、Runs、Evidence 与 Diary 全量织入时间线。
  - `frontend/src/components/QuickCaptureModal.vue`: 顶栏一键唤起 30 秒轻量实验快速沉淀弹窗。
  - `frontend/src/components/UserGuideModal.vue`: 顶栏一键唤起 9 章节内置使用指南与 API 示例代码。
  - `start.bat`: Windows 动态一键启动脚本。
- **Core Research Foundations**:
  - 8-tier Hypothesis Lifecycle (`ACTIVE`, `SUPPORTED`, `WEAKENED`, `REFUTED`, `TESTING`, `STALE`).
  - Multi-Run Horizontal Comparison Matrix (`compare_runs`).
  - Evidence Ledger with Supporting vs Contradicting Balance.
  - Active Exploration Engine (Types A, B, C, D Portfolio & Discrimination Matrix).
  - DuckDB & RestrictedPython Sandboxed Analysis.
  - Obsidian Vault Bridge with note segregation (`<!-- RESEARCHOS:START -->`).
  - Privacy Gateway with 4-tier classification & 3-gate evaluation.
  - Local AI (Ollama) & BYOK Cloud API (DeepSeek / OpenAI) with Zero-LLM fallback.

---

## 3. Test & Build Status
- **Backend Tests**: `61 / 61 PASS (100%)` (`pytest tests/ -v` 50.36s)
- **Frontend Build**: `npm run build` **PASS (1.15s, 0 errors)**

---

## 4. Maintenance & Evolution Policy
- **Feature Freeze**: 本版本已正式锁定。不再进行为了增加功能数量的主动开发。
- **Feedback-Driven**: 后续维护严格由科研用户的实际使用摩擦点与真实痛点驱动。
