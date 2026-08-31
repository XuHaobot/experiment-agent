# ResearchOS (Experiment Agent) 🔬

> **AI-Native, Local-First Personal Research Operating System & Autonomous Experiment Workbench**  
> *A full-closure scientific platform bridging literature deep reading, evidence slicing, hypothesis formulation, data analytics, experiment code generation, sandboxed execution, one-click debugging, and grounded conclusion derivation.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vuedotjs)](https://vuejs.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Local%20Analytics-FFF000?logo=duckdb)](https://duckdb.org/)
[![RestrictedPython](https://img.shields.io/badge/RestrictedPython-Safe%20Sandbox-green)](https://restrictedpython.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 Vision & Philosophy

In traditional scientific research, literature exploration, statistical data analysis, experiment code implementation, hyperparameter telemetry, and post-mortem conclusions are often scattered across disconnected tools (Zotero, Jupyter notebooks, terminal logs, and chat windows).

**ResearchOS** is an **AI-native research operating system** built for long-term day-to-day use by researchers. Adhering to strict **Local-First** principles, it eliminates fake data and LLM hallucinations. Through rigorous **multi-hop data lineage and causal graph provenance**, ResearchOS unifies fragmented scientific assets into a verifiable, deterministic loop:

```
                    ┌─────────────────────────┐
                    │ 1. Scientific Literature│ (OpenAlex / arXiv / S2 / Local PDF)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  2. Evidence Slices     │ (Page X · Section Y · Para #Z)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  3. Research Hypothesis │ (Testing / Supported / Refuted)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  4. Experiment Protocol │ (Parameter Space & Objectives)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  5. Structured Dataset  │ (DuckDB / SQLite / CSV Analytics)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  6. Execution Runs      │ (RestrictedPython / Jupyter / MLflow)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  7. Research Artifacts  │ (Charts / Notebooks / Data Reports)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  8. Grounded Conclusion │ (Strictly anchored to verifiable evidence)
                    └────────────┬────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  9. Next Action & HITL  │ (High-information-gain next trials)
                    └─────────────────────────┘
```

---

## ✨ Key Features & Capabilities

### 1. 📚 Literature Deep Reading & PDF Evidence Slicing
- **Cross-Source Academic Search**: Query OpenAlex, arXiv, and Semantic Scholar via official open APIs.
- **Local PDF Parsing**: Extract structural pages, sections (`Abstract`, `Method`, `Experiments`, etc.), and paragraph text streams.
- **Precise Evidence Slicing**: Directly extract paragraphs from PDF articles, tagged with `Page X · Section Y · Para #Z`, and store them as atomic Evidence slices.
- **Grounded Paper QA**: Chat with paper content with mandatory citations including exact page and section references.

### 2. 📊 Multi-Dataset Relationship Discovery & Analysis Wizard
- **Automated Schema Inference**: Compare schema columns across multiple datasets to discover foreign key join paths (explicitly marked with `source="ai_inference"`).
- **DuckDB Local Analytics Engine**: Fast, in-process SQL execution over local CSV/Parquet files with automatic in-memory SQLite fallback.
- **Interactive Analysis Wizard**: Translate natural language intent (e.g., *"Compare mean response differences between group A and B"*) into actionable SQL and Python workflows, automatically saving results as Analysis Artifacts.

### 3. 💻 Experiment Code Generation & One-Click Debugger
- **Context-Aware Code Synthesis**: Read Project, Hypothesis, Experiment protocol, and Dataset schemas to generate production-grade Python scripts (data loading $\to$ preprocessing $\to$ modeling $\to$ Matplotlib visualization).
- **Sandboxed Safe Execution**: Run scripts inside a RestrictedPython environment equipped with `numpy`, `pandas`, `scipy`, and `matplotlib`.
- **Intelligent Diagnosis & Auto-Patching**: Automatically diagnose runtime errors (such as `KeyError` or `ZeroDivisionError`), generate patches, and retry execution (enforced with a strict 3-retry safety barrier).

### 4. 🧠 Research Memory & Anti-Hallucination Grounding
- **Evidence-Based Grading**: All answers are systematically graded into `SUPPORTED` (backed by experimental evidence), `PARTIALLY_SUPPORTED` (literature prior or partial reasoning), or `UNSUPPORTED` (refusal when unproven).
- **Zero Fake Data / Zero Hallucination**: Unverified hypotheses are explicitly refused without inventing fake runs or metrics.
- **Bidirectional Causal Graph**: Trace full ancestry backwards from any conclusion: `Conclusion → Evidence → Artifact/Run → Dataset/Experiment → Hypothesis → Paper → Project`.

### 5. 🛡️ ToolRegistry & Human-In-The-Loop (HITL) Guard
- **28 Built-In Scientific Tools**: Fully registered with risk classifications (LOW / MEDIUM / HIGH).
- **Security & Permission Enforcement**: High-risk execution tools (`execute_run`, `run_experiment`) are intercepted by the HITL approval workflow, requiring explicit user sign-off before dispatch.

---

## 🖥️ Scientific IDE Overview

- **Research Cockpit**: Real-time cockpit tracking research questions, hypothesis coverage, best run telemetry, and epistemic uncertainty state.
- **Research Timeline**: Chronological trail of hypotheses, data imports, analysis executions, and conclusions.
- **Causal Graph Explorer**: Interactive node graph visualizing bidirectional lineage across all scientific entities.
- **Literature & PDF Workbench**: Cross-database search, structured PDF reader, and paragraph evidence clipper.
- **Data Analytics Workbench**: Sandboxed Python editor, parameter sensitivity analyzer, and Analysis Wizard.
- **Experiment & Coder Workbench**: Protocol designer, automated Python code synthesizer, execution tracker, and AI debugger.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher (for frontend build)
- **Operating System**: Windows, macOS, or Linux

### 2. Backend Setup
Clone the repository and prepare the virtual environment:
```bash
git clone https://github.com/XuHaobot/experiment-agent.git
cd experiment-agent

# Create and activate virtual environment
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Configure your LLM endpoint (Optional; defaults to deterministic local-first mode without API key):
```bash
cp .env.example .env
```
Edit `.env` to configure your OpenAI-compatible API:
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

### 3. Frontend Build
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run the Application
```bash
python backend/main.py
```
Open your browser and navigate to: `http://localhost:5001`

---

## 🧪 Comprehensive Test Suites

ResearchOS includes full automated end-to-end regression test suites:

```bash
# 1. V2.4 Deep Research Productivity (PDF parsing, Analysis Wizard, Code Generator & Debugger)
python tests/test_v24_deep_research.py

# 2. V2.3 Scientific Closure & Provenance Acceptance (14-step verification)
python tests/test_v23_research_closure.py

# 3. V2.2 Open Research Stack Integration (OpenAlex / arXiv / DuckDB / Jupyter / MLflow)
python tests/test_v22_open_research_stack.py

# 4. V2.1 Research Workflow & Memory Grounding
python tests/test_v21_research_workflow.py

# 5. P0 Architectural Security & HITL Acceptance
python tests/test_p0_acceptance.py
```

---

## 📂 Repository Structure

```text
experiment-agent/
├── backend/
│   ├── agent/                 # Agent Core, ToolRegistry (28 tools) & HITL Guard
│   │   ├── security/          # Permission validation & approval ledger (guard.py)
│   │   └── tools/             # Tool registry singleton (registry.py)
│   ├── domain/                # Core domain business logic (Local-first, zero cloud DB)
│   │   ├── project.py         # Research projects & core questions
│   │   ├── paper.py           # Paper entities & PDF evidence slicing
│   │   ├── hypothesis.py      # Scientific hypothesis lifecycle
│   │   ├── experiment.py      # Experiment protocols
│   │   ├── dataset.py         # Dataset management & summaries
│   │   ├── run.py             # Physical execution runs & telemetry
│   │   ├── artifact.py        # Research artifacts (charts/reports/notebooks)
│   │   ├── conclusion.py      # Grounded scientific conclusions
│   │   ├── memory.py          # Epistemic research memory & grounded Q&A
│   │   └── experiment_coder.py# Code synthesis & debugging domain services
│   ├── integrations/          # External ecosystem adapters
│   │   ├── literature/        # OpenAlex / arXiv / Semantic Scholar / PDF Reader
│   │   ├── data/              # DuckDB / SQLite SQL engine & Analysis Wizard
│   │   ├── notebook/          # Jupyter .ipynb parser & artifact ingestion
│   │   ├── experiment/        # MLflow local runs synchronizer
│   │   └── execution/         # RestrictedPython / DockerRunner sandbox execution
│   └── main.py                # FastAPI entry point & RESTful routes
├── frontend/                  # Vue3 Scientific IDE frontend
│   ├── src/
│   │   ├── components/        # Panels (Literature, Analysis, Artifact, Conclusion)
│   │   └── views/             # ProjectDetailView.vue full scientific workspace
│   └── dist/                  # Static production build
├── data/                      # Local-First disk storage
│   ├── projects/              # Project JSON metadata
│   ├── papers/                # Saved papers & extracted PDF structures
│   ├── datasets/              # Real CSV / Parquet data files
│   ├── runs/                  # Physical run telemetry logs
│   ├── artifacts/             # Persisted charts & reports
│   └── conclusions/           # Verified conclusions
├── tests/                     # Automated end-to-end test suites
└── docs/                      # Technical specifications & audit reports
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
