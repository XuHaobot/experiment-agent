"""
Markdown Entity Renderers & Content Merge Engine
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from backend.vault.frontmatter import format_frontmatter, parse_frontmatter
from backend.vault.wikilinks import wikilink

START_TAG = "<!-- RESEARCHOS:START -->"
END_TAG = "<!-- RESEARCHOS:END -->"
SECTION_REGEX = re.compile(
    rf"{re.escape(START_TAG)}(.*?){re.escape(END_TAG)}",
    re.DOTALL,
)


def merge_with_existing(
    frontmatter_meta: Dict[str, Any],
    managed_body: str,
    existing_content: Optional[str] = None,
) -> str:
    """
    Safely merges new ResearchOS managed content with existing user Markdown.
    Guarantees user notes outside the RESEARCHOS tags are 100% preserved.
    """
    if not existing_content or not existing_content.strip():
        # New file
        fm_block = format_frontmatter(frontmatter_meta)
        return f"{fm_block}\n\n{START_TAG}\n{managed_body.strip()}\n{END_TAG}\n\n## My Notes\n\n"

    existing_meta, existing_body = parse_frontmatter(existing_content)
    
    # Merge frontmatter: keep existing user tags if present, update status/updated_at
    merged_meta = dict(existing_meta)
    merged_meta.update(frontmatter_meta)
    fm_block = format_frontmatter(merged_meta)

    # Check if section markers exist
    if START_TAG in existing_body and END_TAG in existing_body:
        # Replace only the managed block
        new_body = SECTION_REGEX.sub(
            f"{START_TAG}\n{managed_body.strip()}\n{END_TAG}",
            existing_body,
            count=1,
        )
        return f"{fm_block}\n\n{new_body.lstrip()}"
    else:
        # Existing file without tags: prepend managed block and preserve all existing content as user notes
        user_notes = existing_body.strip()
        return f"{fm_block}\n\n{START_TAG}\n{managed_body.strip()}\n{END_TAG}\n\n{user_notes}\n"


# =============================================================================
# Entity Markdown Renderers
# =============================================================================

def render_project(project: Dict[str, Any]) -> str:
    pid = project.get("id", "project")
    meta = {
        "researchos_id": pid,
        "entity_type": "project",
        "title": project.get("name", "Project"),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at"),
        "epistemic_status": "PROJECT",
        "source": "researchos",
    }
    
    questions = project.get("questions", [])
    q_links = [f"- {wikilink(q.get('id'), q.get('text'))}" for q in questions]
    exp_ids = project.get("experiment_ids", [])
    exp_links = [f"- {wikilink(eid)}" for eid in exp_ids]

    body = f"""# Project: {project.get('name')}

> [!abstract] Research Overview
> {project.get('description') or 'No description provided.'}

## Research Questions
{chr(10).join(q_links) if q_links else '- None recorded yet.'}

## Experiments
{chr(10).join(exp_links) if exp_links else '- None configured yet.'}
"""
    return meta, body


def render_question(question: Dict[str, Any], project_id: str) -> str:
    qid = question.get("id", "q_001")
    meta = {
        "researchos_id": qid,
        "entity_type": "question",
        "project_id": project_id,
        "created_at": question.get("created_at"),
        "epistemic_status": "OBSERVATION",
        "source": "researchos",
    }
    body = f"""# Research Question: {qid}

> [!question] Core Question
> {question.get('text', '')}

## Belongs to Project
- {wikilink(project_id)}
"""
    return meta, body


def render_hypothesis(
    hyp: Dict[str, Any],
    evidence_list: Optional[List[Dict[str, Any]]] = None,
    experiments_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    hid = hyp.get("id", "hyp_001")
    meta = {
        "researchos_id": hid,
        "entity_type": "hypothesis",
        "project_id": hyp.get("project_id"),
        "title": hyp.get("title"),
        "status": hyp.get("status", "testing"),
        "epistemic_status": "HYPOTHESIS",
        "created_at": hyp.get("created_at"),
        "updated_at": hyp.get("updated_at"),
        "source": "researchos",
    }
    
    ev_links = []
    if evidence_list:
        for ev in evidence_list:
            ev_links.append(f"- {wikilink(ev.get('id'), ev.get('claim', ev.get('source_location')))}")
    
    exp_links = []
    if experiments_list:
        for exp in experiments_list:
            exp_links.append(f"- {wikilink(exp.get('id'), exp.get('task'))}")

    body = f"""# Hypothesis: {hyp.get('title')}

> [!hypothesis] Core Claim
> {hyp.get('description') or hyp.get('title')}

**Status**: `{hyp.get('status', 'testing').upper()}`

## Linked Research Question
- {wikilink(hyp.get('question_id')) if hyp.get('question_id') else 'Not linked'}

## Evidence Ledger
{chr(10).join(ev_links) if ev_links else '- No evidence attached yet.'}

## Verifying Experiments
{chr(10).join(exp_links) if exp_links else '- No experiment runs attached yet.'}
"""
    return meta, body


def render_experiment(
    exp: Dict[str, Any],
    runs_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    eid = exp.get("id", "exp_001")
    meta = {
        "researchos_id": eid,
        "entity_type": "experiment",
        "project_id": exp.get("project_id"),
        "task": exp.get("task"),
        "model": exp.get("model"),
        "dataset": exp.get("dataset"),
        "epistemic_status": "EXPERIMENT",
        "created_at": exp.get("created_at"),
        "source": "researchos",
    }

    params_json = json.dumps(exp.get("params", {}), ensure_ascii=False, indent=2)
    runs_lines = []
    if runs_list:
        for r in runs_list:
            metrics_str = json.dumps(r.get("metrics", {}), ensure_ascii=False)
            runs_lines.append(f"- **{r.get('id')}** (`{r.get('status')}`): Metrics = `{metrics_str}`")

    body = f"""# Experiment Protocol: {exp.get('task')}

> [!example] Protocol Objective
> {exp.get('conclusions') or exp.get('expected_outcome') or 'Empirical parameter ablation run.'}

## Target Architecture & Dataset
- **Model**: `{exp.get('model', 'N/A')}`
- **Dataset**: `{exp.get('dataset', 'N/A')}`

## Configured Parameters
```json
{params_json}
```

## Physical Runs Telemetry
{chr(10).join(runs_lines) if runs_lines else '- No physical run records yet.'}
"""
    return meta, body


def render_evidence(ev: Dict[str, Any]) -> str:
    ev_id = ev.get("id", "ev_001")
    meta = {
        "researchos_id": ev_id,
        "entity_type": "evidence",
        "source_type": ev.get("source_type", ev.get("type", "paper")),
        "source_id": ev.get("source_id", ev.get("paper_id")),
        "polarity": "SUPPORT" if ev.get("supports", True) else "CONTRADICT",
        "confidence": "HIGH",
        "epistemic_status": "EVIDENCE",
        "created_at": ev.get("created_at"),
        "source": "researchos",
    }
    
    src_link = wikilink(ev.get("source_id", ev.get("paper_id")), ev.get("paper_title"))
    hyp_link = wikilink(ev.get("hypothesis_id")) if ev.get("hypothesis_id") else "None"

    body = f"""# Evidence: {ev_id}

> [!quote] Grounded Excerpt / Metric
> "{ev.get('snippet', ev.get('text', ''))}"

## Origin Source
- **Type**: `{ev.get('source_type', 'paper')}`
- **Source**: {src_link}
- **Location**: `{ev.get('source_location', 'N/A')}`

## Associated Hypothesis
- {hyp_link}
"""
    return meta, body


def render_conclusion(conc: Dict[str, Any]) -> str:
    cid = conc.get("id", "conc_001")
    meta = {
        "researchos_id": cid,
        "entity_type": "conclusion",
        "project_id": conc.get("project_id"),
        "hypothesis_id": conc.get("hypothesis_id"),
        "confidence": conc.get("confidence", "high"),
        "epistemic_status": "CONCLUSION",
        "created_at": conc.get("created_at"),
        "source": "researchos",
    }

    ev_refs = conc.get("evidence_refs", [])
    ev_lines = []
    for ref in ev_refs:
        ref_id = ref.get("id")
        ref_type = ref.get("type", "evidence")
        ev_lines.append(f"- [[{ref_id}|{ref_type.upper()} {ref_id}]]: {ref.get('snippet', '')}")

    body = f"""# Scientific Conclusion: {cid}

> [!success] Grounded Finding
> {conc.get('text', '')}

**Confidence**: `{conc.get('confidence', 'high').upper()}`

## Validates Hypothesis
- {wikilink(conc.get('hypothesis_id')) if conc.get('hypothesis_id') else 'Global finding'}

## Supporting Evidence Sources
{chr(10).join(ev_lines) if ev_lines else '- Direct empirical observation.'}
"""
    return meta, body


def render_paper(
    paper: Dict[str, Any],
    evidence_list: Optional[List[Dict[str, Any]]] = None,
) -> str:
    pid = paper.get("id", "paper_001")
    meta = {
        "researchos_id": pid,
        "entity_type": "paper",
        "title": paper.get("title"),
        "year": paper.get("year"),
        "doi": paper.get("doi"),
        "source_provider": paper.get("source"),
        "epistemic_status": "OBSERVATION",
        "created_at": paper.get("created_at"),
        "source": "researchos",
    }

    ev_lines = []
    if evidence_list:
        for ev in evidence_list:
            ev_lines.append(f"- {wikilink(ev.get('id'), ev.get('source_location', 'Evidence Slice'))}")

    authors_str = ", ".join(paper.get("authors", [])) if isinstance(paper.get("authors"), list) else str(paper.get("authors", ""))

    body = f"""# Literature: {paper.get('title')}

> [!info] Academic Metadata
> - **Authors**: {authors_str or 'Unknown'}
> - **Year**: `{paper.get('year', 'N/A')}`
> - **DOI**: `{paper.get('doi', 'N/A')}`
> - **Source**: `{paper.get('source', 'OpenAlex/arXiv')}`

## Abstract / Summary
{paper.get('abstract') or paper.get('snippet') or 'No abstract provided.'}

## Extracted ResearchOS Evidence Slices
{chr(10).join(ev_lines) if ev_lines else '- No evidence slices extracted yet.'}
"""
    return meta, body


def render_artifact(art: Dict[str, Any]) -> str:
    aid = art.get("id", "art_001")
    meta = {
        "researchos_id": aid,
        "entity_type": "artifact",
        "project_id": art.get("project_id"),
        "name": art.get("name"),
        "artifact_type": art.get("artifact_type", art.get("type", "analysis")),
        "mime_type": art.get("mime_type", "application/json"),
        "epistemic_status": "FACT",
        "created_at": art.get("created_at"),
        "source": "researchos",
    }

    body = f"""# Artifact: {art.get('name', aid)}

> [!note] Artifact Descriptor
> - **Type**: `{art.get('artifact_type', art.get('type', 'analysis'))}`
> - **Local Path / Source**: `{art.get('local_path', art.get('path', 'ResearchOS managed'))}`

## Description & Summary
{art.get('summary') or art.get('description') or 'Statistical artifact generated by analysis pipeline.'}
"""
    return meta, body
