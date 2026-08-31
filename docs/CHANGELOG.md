# Changelog

All notable changes to the ResearchOS (Experiment Agent) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

---

## [V2.6.0] - 2026-08-31 [STABLE / PRODUCT-FROZEN]

### Added
- **AI-Agnostic Research Workflow & Final Stabilization**:
  - Added `execution_origin` (`LOCAL_SANDBOX`, `EXTERNAL_LOCAL`, `REMOTE_SERVER`, `CODEX`, `CLAUDE_CODE`, `MANUAL`, `IMPORTED`) and Git lineage (`git_commit`, `git_branch`, `repository`) to `ExperimentRun` in `backend/domain/run.py`.
  - Added `Quick Capture` 30-second research logging (`what_i_did`, `tools_used`, `what_happened`, `what_surprised_me`, `current_belief`, `next_step`) in `backend/domain/session.py`.
  - Added `generate_external_prompt` Prompt Bridge for Codex / Claude Code / ChatGPT.
  - Added `frontend/src/components/QuickCaptureModal.vue` accessible with 1-click from the top navigation bar.
  - Added `frontend/src/components/UserGuideModal.vue` with 9 interactive chapters and copyable Python API integration code.
  - Added `frontend/src/components/ResearchDiaryPanel.vue` and `frontend/src/components/RunComparisonModal.vue`.
  - Added `tests/test_v26_real_research_workflow.py` validating the 20-step real researcher journey (PASS).
  - Added `docs/RESEARCHOS_FINAL_STATUS.md` as the definitive SSOT final product status report.
  - Total automated test coverage: **61/61 PASS (100%)**.

---

## [V2.5.0] - 2026-08-31

### Added
- **Local AI Gateway (Phase 15)**:
  - Added `backend/llm/base.py` with `LLMProvider` interface and dataclasses.
  - Added `backend/llm/providers/ollama.py` for Ollama local inference and model discovery.
  - Added `backend/llm/providers/openai_compatible.py` for standard cloud/BYOK endpoints.
  - Added `backend/llm/providers/mock.py` for deterministic offline testing.
  - Added `backend/llm/gateway.py` with `LLMGateway` and routing policies (`LOCAL_ONLY`, `LOCAL_PREFERRED`, `CLOUD_ALLOWED`).
  - Added `backend/llm/context.py` with `ResearchContext`, `ContextItem`, and `ContextPlanner`.
- **Privacy Boundary & Gate (Phase 15)**:
  - Added `backend/security/classification.py` for 4-tier data classification (`PUBLIC`, `INTERNAL`, `SENSITIVE`, `RESTRICTED`).
  - Added `backend/security/privacy_gateway.py` enforcing `ALLOW`, `ASK`, and `DENY` hard block constraints prior to LLM calls.
  - Added `backend/security/audit.py` recording privacy decisions to `data/audit/privacy_audit.jsonl`.
- **Obsidian Knowledge Layer & Vault Bridge (Phase 16)**:
  - Added `backend/vault/` subsystem with `models.py`, `frontmatter.py`, `wikilinks.py`, `renderer.py`, `manifest.py`, `exporter.py`, `importer.py`.
  - Implemented safe Markdown projection with `<!-- RESEARCHOS:START -->` and `<!-- RESEARCHOS:END -->` tags, guaranteeing 100% preservation of user personal notes.
  - Implemented YAML Frontmatter generation with `epistemic_status` support.
  - Implemented stable ID Wikilinks (`[[H-001]]`, `[[EXP-001]]`, `[[ev_pdf_...]]`, `[[conc_...]]`) mapping the research causal graph into Obsidian Graph View.
  - Implemented `ResearchOS/manifest.json` tracking managed files, versions, and hashes.
- **Research Memory 2.0 & Epistemic Anti-Lock-in (Phase 17)**:
  - Added `backend/domain/epistemic.py` with 10-tier `EpistemicStatus` enum and transition validation.
  - Added `build_evidence_balance` in `backend/domain/memory.py` calculating Supporting vs Contradicting vs Unknown metrics.
  - Added `discover_unexplored_space` in `backend/domain/memory.py` identifying parameter blind spots and sampling gaps.
  - Added `generate_alternative_hypotheses` in `backend/domain/memory.py` generating grounded competitive explanations (`AI_SUGGESTION`).
- **Active Exploration Engine & Epistemic Pruning (Phase 18)**:
  - Added `backend/domain/exploration.py` implementing `CandidateExperimentEngine` (Type A Exploit, Type B Discriminate, Type C Explore, Type D Replicate).
  - Implemented `detect_pseudo_exploration` flagging micro-variations and saturation loops in parameter space.
  - Implemented `build_hypothesis_discrimination_matrix` calculating prediction divergence across competing hypotheses.
  - Implemented `analyze_epistemic_pruning` providing non-destructive hypothesis pruning and resource allocation advisory.
  - Implemented `approve_candidate_experiment` creating formal experiment drafts with complete causal lineage.
  - Added REST APIs: `GET /api/projects/{id}/exploration/candidates`, `GET /api/projects/{id}/exploration/discrimination`, `GET /api/projects/{id}/exploration/pruning`, `POST /api/projects/{id}/exploration/approve`.
  - Added `frontend/src/components/ExplorePanel.vue` and integrated Active Explore tab in `frontend/src/views/ProjectDetailView.vue`.
  - Added test suite `tests/test_v25_phase18_exploration.py` (17/17 PASS).

---

## [V2.4.0] - 2026-08-31

### Added
- **PDF Evidence Slicing & Grounded Q&A (P0-A)**:
  - Added `backend/integrations/literature/pdf_reader.py` for pypdf page extraction, paragraph streaming, section identification, and MD5 integrity verification.
  - Added `create_paper_evidence_slice` in `backend/domain/paper.py` for exact evidence slices (`Page X · Section Y · Para #Z`).
  - Added `ask_paper_question` for grounded paper Q&A with structured citations.
  - Added PDF read and slice modal in `frontend/src/components/LiteraturePanel.vue`.
- **Multi-Dataset Relationship Discovery & Analysis Wizard (P0-B)**:
  - Added `backend/integrations/data/relationship.py` for automated schema join-key detection with confidence scoring and `source="ai_inference"` tagging.
  - Added `backend/integrations/data/wizard.py` for translating natural language analysis intents into DuckDB/SQLite SQL and Python plans.
  - Added automated physical `Artifact` persistence for analysis executions.
  - Added Analysis Wizard and Schema Relations tabs in `frontend/src/components/DataAnalysisPanel.vue`.
- **Experiment Code Synthesis & Intelligent Debugger (P0-C)**:
  - Added `backend/integrations/execution/generator.py` for scientific context-aware Python experiment code generation with complete provenance metadata.
  - Added `backend/integrations/execution/debugger.py` for automated traceback diagnosis and code patch generation.
  - Added hard safety gate capping automatic retry attempts at 3.
  - Added Experiment Coder and Debugger modal in `frontend/src/views/ProjectDetailView.vue`.
- **Agent Governance & ToolRegistry Expansion**:
  - Registered 9 new tools in `ToolRegistry` (reaching 28 registered tools total) with explicit risk tiers and HITL gating.
- **Testing & Product Validation**:
  - Added `tests/test_v24_deep_research.py` covering deep research productivity components.
  - Added `tests/test_v24_user_journey.py` covering a complete 16-step researcher workflow from project creation to loop closure.
  - Added `docs/V2.4_PRODUCT_VALIDATION.md` documenting user feedback and requirement inputs for V2.5.

### Fixed
- Fixed RestrictedPython AST sandbox import resolution in `backend/domain/data_agent.py` by configuring whitelisted module resolvers for scientific packages (`numpy`, `pandas`, `scipy`, `matplotlib`, `duckdb`).

---

## [V2.3.0] - 2026-08-20

### Added
- **Zero-Hallucination Research Memory**:
  - Added `backend/domain/memory.py` with structured SQLite backing (`data/memory.db`).
  - Implemented 3-tier fact classification (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`).
- **Research Timeline & Cockpit**:
  - Added `backend/domain/timeline.py` and `/api/projects/{id}/timeline` endpoint.
  - Added `/api/projects/{id}/cockpit` for aggregated hypothesis validation progress and uncertainty monitoring.
  - Added `frontend/src/components/ExperimentTimeline.vue`.
- **Causal Lineage & Multi-Hop Backward Tracing**:
  - Added `/api/projects/{id}/lineage/backward` for traversing from conclusions to raw evidence, runs, datasets, and literature.
- **Audit & Closure Test Suites**:
  - Added `tests/test_research_loop_audit.py` and `tests/test_v23_research_closure.py`.
  - Added `docs/V2.3_PRE_AUDIT.md`, `docs/V2.3_MOCK_AUDIT.md`, `docs/V2.3_PROVENANCE_REPORT.md`, `docs/V2.3_E2E_CLOSURE_REPORT.md`.

### Changed
- Removed all non-test mock fallbacks to guarantee 100% genuine data lineage.

---

## [V2.2.0] - 2026-08-10

### Added
- **Open Research Literature Stack**:
  - Added adapters for OpenAlex API, arXiv API, and Semantic Scholar API (`backend/integrations/literature/`).
- **Local Data Analytics Engine**:
  - Integrated `DuckDB` (`backend/integrations/data/duckdb.py`) for high-performance SQL analytics with automatic in-memory SQLite fallback.
- **Execution Sandbox & HITL Governance**:
  - Added `RestrictedPythonRunner` for AST-isolated code execution.
  - Added `backend/agent/tools/registry.py` (`ToolRegistry`) with `SAFE`, `LOW`, `MEDIUM`, `HIGH` risk levels.
  - Added HITL (Human-in-the-Loop) permission gates and approval tickets (`data/approvals/`).
- **Jupyter & MLflow Adapters**:
  - Added `backend/integrations/notebook/jupyter.py` and `backend/integrations/experiment/mlflow.py`.
- **Test Suite**:
  - Added `tests/test_v22_open_research_stack.py`.

---

## [V2.1.0] - 2026-07-28

### Added
- **Domain Layer Refactoring**:
  - Introduced `backend/domain/`: `project.py`, `hypothesis.py`, `dataset.py`, `analysis.py`, `artifact.py`, `conclusion.py`, `run.py`, `next_experiment.py`.
  - Implemented state transitions for hypotheses (`testing`, `supported`, `refuted`).
- **Vue 3 Research UI Components**:
  - Added `ProjectView.vue`, `ProjectDetailView.vue`, `HypothesisPanel.vue`, `DataAnalysisPanel.vue`, `ArtifactPanel.vue`, `ConclusionPanel.vue`, `NextExperimentPanel.vue`.
- **Test Suite**:
  - Added `tests/test_v21_research_workflow.py`.

---

## [V2.0.0] - 2026-06-14

### Added
- **Full-Stack Architecture Transformation**:
  - Replaced Streamlit UI with FastAPI backend (`backend/main.py`) + Vue 3 frontend (`frontend/`).
  - Added Function Calling Agent (`src/agent_v2.py`).
  - Added ChromaDB vector store for semantic retrieval (`src/vector_store.py`).
  - Added interactive Knowledge Graph visualization powered by `vis-network` (`src/graph/`).
  - Added Server-Sent Events (SSE) streaming output.

---

## [V1.0.0] - 2026-05-10

### Added
- Minimal Streamlit single-page application (`app.py`).
- Basic rule-based and regex extraction tools (`src/tools/`).
- Local file persistence for experiment records (`data/records/`) and Markdown reports (`data/reports/`).
- Simple keyword-based query search.
