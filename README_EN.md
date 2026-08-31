# ResearchOS (Experiment Agent) 🔬

> **AI-Agnostic, Local-First Personal Research Workspace & Evidence Layer**  
> *A full-closure scientific platform bridging literature deep reading, hypothesis tracking, external & local experiment runs, multi-run comparison, empirical evidence balances, active exploration, research diary, and Obsidian vault integration.*

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

## 📖 Vision & Philosophy

In traditional scientific research, literature exploration, statistical data analysis, experiment code implementation, hyperparameter telemetry, and post-mortem conclusions are often scattered across disconnected tools (Zotero, Jupyter notebooks, terminal logs, and chat windows).

**ResearchOS** is an **AI-Agnostic, Local-First Personal Research Workspace** built for long-term day-to-day use by researchers. It does not attempt to replace your external AI assistants (OpenAI Codex, Claude Code, ChatGPT) or your computing hardware (local RTX 4090, university HPC clusters). Instead, it serves as the **central cognitive ledger and workflow hub**:

```text
Researcher (Intuition & Literature)
   │
   ├── External LLM (Codex / Claude Code / ChatGPT / DeepSeek / Local Ollama)
   │       │
   │       ├── Synthesizes PyTorch / JAX scripts
   │       ├── Executes training runs (Local GPU / Remote HPC / Server)
   │       └── Yields logs, CSV metrics & checkpoints
   │
   └── ResearchOS (Central Evidence & Memory Layer)
          │
          ├── Research Question (Core Scientific Inquiries)
          ├── Hypothesis (8-tier Lifecycle: Active, Supported, Weakened, Refuted...)
          ├── Experiment & Runs (Decoupled Protocols & Run Telemetry)
          ├── Quick Capture (30s frictionless workflow & session logging)
          ├── Multi-Run Comparison Matrix (Automatic param alignment & BEST peak detection)
          ├── Evidence Ledger (Supporting vs Contradicting balance)
          ├── Grounded Conclusions (Strictly anchored to verifiable run/paper evidence)
          ├── Active Exploration Engine (Type A/B/C/D Portfolios & Discrimination Matrix)
          ├── Research Diary (USER_BELIEF records, protected from AI modification)
          ├── Obsidian Vault Bridge (Bidirectional export with user note paragraph isolation)
          └── External LLM Prompt Bridge (1-click export of context-rich prompts for Codex)
```

---

## ✨ Key Features & Capabilities (V2.6.0)

### 1. ⚡ Quick Capture & External AI Workflow (AI-Agnostic)
- **30-Second Quick Capture**: A dedicated lightweight modal to record what you did, what tools you used (Codex, Claude Code, Manual, etc.), what happened, surprises, and next steps in 30 seconds.
- **External Run Execution Origin**: Native support for `LOCAL_SANDBOX`, `CODEX`, `CLAUDE_CODE`, `EXTERNAL_LOCAL`, `REMOTE_SERVER`, `MANUAL`, and `IMPORTED`.
- **Git Commit Lineage**: Bind runs directly to `git_commit`, `git_branch`, and `repository`.
- **External LLM Prompt Bridge**: 1-click export of structured academic prompts containing your current hypothesis, best parameter baselines, failed negative lessons, and unexplored parameter gaps—ready to paste into ChatGPT/Codex/Claude.

### 2. 📊 Multi-Run Horizontal Comparison & CSV Import
- **CSV Batch Ingestion**: Drag-and-drop external experiment CSV files; automatically detect schema and generate multiple atomic `ExperimentRun` records.
- **Side-by-Side Comparison Matrix**: Check multiple runs to generate a unified comparison matrix aligning all independent hyperparameter variables and dependent metrics, highlighting the optimal configuration (👑 BEST) and inflection points.

### 3. 🔬 8-Tier Hypothesis Lifecycle & Evidence Balance
- **Epistemic State Machine**: Hypotheses transition dynamically between `ACTIVE`, `SUPPORTED`, `WEAKENED`, `REFUTED`, `TESTING`, and `STALE`.
- **Evidence Balance Ledger**: Real-time ratio tracking of Positive Supporting vs Negative Contradicting evidence to actively combat Confirmation Bias.
- **Grounded Conclusions**: Conclusions must cite specific Run IDs or paper paragraph slices (`Page X · Sec Y`), eliminating hallucinated findings.

### 4. 🧭 Active Exploration Engine & Epistemic Pruning
- **Multi-Objective Exploration Portfolio**:
  - `Type A (EXPLOIT)`: Fine-grained tuning around known optima.
  - `Type B (DISCRIMINATE)`: Decoupled trials designed to generate diverging predictions across competing hypotheses.
  - `Type C (EXPLORE)`: Leaping into unsampled parameter gap regions.
  - `Type D (REPLICATE)`: Multi-seed reproducibility runs to quantify error bars.
- **Hypothesis Discrimination Matrix**: Visual comparison of theoretical predictions across hypotheses.
- **Pseudo-Exploration Warning**: Automatically detects redundant micro-tweaks in saturated parameter clusters.
- **Non-Destructive Pruning Advisor**: Recommends resource deprioritization for refuted hypotheses without ever automatically deleting user data.

### 5. 📔 Research Diary & Research Sessions
- **Research Diary**: Daily scratchpad for personal intuition, reflections, and informal observations, strictly classified as `USER_BELIEF` (AI is forbidden from altering or fabricating diary notes).
- **Research Sessions**: Lightweight tracking of continuous work sessions across literature, datasets, runs, and conclusions.

### 6. 📚 Obsidian Vault Bridge
- **Bidirectional Note Projection**: Synchronize structured research objects into Obsidian folders (`01_Projects`, `02_Hypotheses`, `03_Experiments`, `05_Conclusions`) with YAML frontmatter and `[[Wikilinks]]`.
- **100% User Note Paragraph Isolation**: Uses `<!-- RESEARCHOS:START -->` boundary markers, guaranteeing that personal notes written inside Obsidian are never overwritten.

### 7. 🛡️ Local AI & 3-Gate Privacy Protection
- **Zero-LLM Fallback**: Works 100% offline without requiring any local LLM or cloud API keys.
- **Local Ollama & Cloud BYOK**: Optional connection to local Ollama (e.g. `qwen2.5-coder`) or lightweight cloud API keys (DeepSeek / OpenAI) with 0 GPU VRAM consumed on training machines.
- **Privacy Boundary**: 4-tier data classification (`PUBLIC`, `INTERNAL`, `SENSITIVE`, `RESTRICTED`) and 3-gate evaluation (`ALLOW`, `ASK`, `DENY`).

### 8. 📖 In-App Interactive User Guide
- Top navigation bar provides instant access to a 9-chapter interactive documentation center with ready-to-copy Python integration code snippets.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python**: 3.10, 3.11, or 3.12
- **Node.js**: 18.0 or higher
- **OS**: Windows, macOS, or Linux

### 2. One-Click Launch (Windows)
Double-click:
```cmd
start.bat
```
This automatically starts:
* **FastAPI Backend**: `http://127.0.0.1:5001` (Interactive API Docs: `http://127.0.0.1:5001/docs`)
* **Vue3 Web UI**: `http://localhost:3000`

### 3. Manual Step-by-Step Launch
```bash
# 1. Clone repository
git clone https://github.com/XuHaobot/experiment-agent.git
cd experiment-agent

# 2. Setup Python environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# 3. Start Backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5001 --reload

# 4. Start Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

---

## ⚡ REST API & Python Integration Example

ResearchOS provides a comprehensive RESTful API for seamless integration with PyTorch training loops, Jupyter Notebooks, or external scripts:

```python
import requests

BASE_URL = "http://127.0.0.1:5001"

# 1. Record an Experiment Run with Git lineage & external origin
run_res = requests.post(f"{BASE_URL}/api/runs", json={
    "experiment_id": "exp_dgcnn_sweep",
    "actual_parameters": {"k": 25, "lr": 1e-4, "residual": True},
    "metrics": {"val_accuracy": 0.912, "loss": 0.098},
    "status": "completed",
    "execution_origin": "CODEX",
    "git_commit": "a82f31c",
    "ai_tool_used": "Codex"
}).json()
print("Saved Run ID:", run_res["id"])

# 2. Compare multiple runs side-by-side
compare_res = requests.post(f"{BASE_URL}/api/runs/compare", json={
    "run_ids": ["run_01", "run_02", run_res["id"]]
}).json()
print("Optimal Configuration:", compare_res["best_run_id"])
print("Key Insights:", compare_res["insights"])

# 3. 30-Second Quick Capture of research session
qc_res = requests.post(f"{BASE_URL}/api/projects/proj_01/quick-capture", json={
    "title": "Residual connection over-smoothing decoupled test",
    "what_i_did": "Implemented initial residual mapping using Codex",
    "what_happened": "Peak accuracy reached 91.2% at k=25",
    "ai_tool_used": "Codex",
    "git_commit": "a82f31c"
}).json()

# 4. Fetch context-rich prompt for your next Codex session
prompt_res = requests.get(f"{BASE_URL}/api/projects/proj_01/external-prompt").json()
print("Copy this prompt to ChatGPT/Codex:\n", prompt_res["prompt_text"])
```

---

## 🧪 Comprehensive Automated Test Suites

ResearchOS includes 61 automated end-to-end regression test suites:

```bash
pytest tests/ -v
```

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

## 📂 Repository Architecture

```text
experiment-agent/
├── backend/
│   ├── domain/                # Core domain entities & business logic
│   │   ├── project.py         # Research projects & core questions
│   │   ├── hypothesis.py      # 8-tier scientific hypothesis lifecycle
│   │   ├── run.py             # Runs, CSV import & multi-run comparison
│   │   ├── session.py         # Quick Capture & External Prompt Bridge
│   │   ├── exploration.py     # Active Exploration (Types A/B/C/D) & Discrimination
│   │   ├── diary.py           # Research diary (USER_BELIEF)
│   │   ├── timeline.py        # Unified research timeline aggregator
│   │   ├── dataset.py         # DuckDB schema inference & SQL query engine
│   │   ├── artifact.py        # SHA256 deduplicated research assets
│   │   └── conclusion.py      # Grounded empirical conclusions
│   ├── vault/                 # Obsidian Vault Bridge subsystem
│   ├── security/              # Data classification & 3-gate privacy gateway
│   ├── llm/                   # Ollama local driver & OpenAI/DeepSeek gateway
│   └── main.py                # FastAPI entry point & REST routes
├── frontend/                  # Vue3 Scientific IDE frontend
│   ├── src/
│   │   ├── components/        # QuickCapture, UserGuide, Explore, Compare, Diary
│   │   └── views/             # ProjectDetailView.vue full scientific workspace
│   └── dist/                  # Static production build
├── data/                      # Local-First JSON & DuckDB storage
├── docs/                      # SSOT documentation & user guides
│   ├── RESEARCHOS_FINAL_STATUS.md # Definitive product status report
│   ├── USER_AND_API_GUIDE.md  # Comprehensive user & API reference manual
│   └── RELEASE_NOTES_V2.6.md  # V2.6.0 stable release notes
├── tests/                     # 61 automated regression test suites
└── start.bat                  # Windows one-click startup script
```

---

## 📜 Documentation

* [**User & Developer Guide**](docs/USER_AND_API_GUIDE.md): Full walkthrough of every panel and complete REST API specifications.
* [**Final Status Report**](docs/RESEARCHOS_FINAL_STATUS.md): Architectural decisions and feature-frozen SSOT.
* [**Release Notes**](docs/RELEASE_NOTES_V2.6.md): V2.6.0 changelog and details.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
