"""
Paper Domain Module — 学术文献实体、PDF 全文解析与证据切片管理
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from backend.integrations.literature.pdf_reader import pdf_reader

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PAPERS_DIR = DATA_DIR / "papers"


def _ensure_dir():
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)


def _paper_folder(paper_id: str) -> Path:
    safe_id = paper_id.replace("/", "_").replace(":", "_")
    folder = PAPERS_DIR / safe_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _paper_meta_path(paper_id: str) -> Path:
    safe_id = paper_id.replace("/", "_").replace(":", "_")
    folder = PAPERS_DIR / safe_id
    if folder.exists() and (folder / "metadata.json").exists():
        return folder / "metadata.json"
    return PAPERS_DIR / f"{safe_id}.json"


def save_paper_to_project(
    project_id: str,
    paper_data: dict[str, Any],
    linked_hypothesis_id: str | None = None,
    linked_question: str | None = None,
) -> dict[str, Any]:
    """
    将文献保存为 Project 关联实体，并可直接建立为初始文献证据 (Literature Evidence)
    """
    _ensure_dir()
    from backend.domain.project import get_project, update_project

    proj = get_project(project_id)
    if not proj:
        raise ValueError(f"Project 不存在: {project_id}")

    raw_id = paper_data.get("paper_id") or paper_data.get("id") or f"paper_{int(time.time()*1000)}"
    safe_id = raw_id.replace("/", "_").replace(":", "_")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    folder = _paper_folder(safe_id)

    record = {
        "id": safe_id,
        "paper_id": raw_id,
        "project_id": project_id,
        "title": paper_data.get("title", "Untitled"),
        "authors": paper_data.get("authors", []),
        "abstract": paper_data.get("abstract", ""),
        "year": paper_data.get("year"),
        "doi": paper_data.get("doi"),
        "url": paper_data.get("url"),
        "source": paper_data.get("source", "openalex"),
        "citation_count": paper_data.get("citation_count", 0),
        "venue": paper_data.get("venue", ""),
        "pdf_url": paper_data.get("pdf_url"),
        "has_pdf": False,
        "pdf_pages": 0,
        "linked_hypothesis_id": linked_hypothesis_id,
        "linked_question": linked_question,
        "metadata": paper_data.get("metadata", {}),
        "created_at": now,
    }

    # 写入 folder/metadata.json 与兼容性的 papers/{safe_id}.json
    (folder / "metadata.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (PAPERS_DIR / f"{safe_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 更新 Project 关联列表
    current_papers = list(proj.get("paper_ids", []))
    if safe_id not in current_papers:
        current_papers.append(safe_id)
        update_project(project_id, {"paper_ids": current_papers})

    logger.info("Paper %s saved to project %s", safe_id, project_id)
    return record


def save_paper_pdf(
    project_id: str,
    paper_id: str,
    pdf_bytes: bytes,
    filename: str = "source.pdf",
) -> dict[str, Any]:
    """保存并解析 PDF 全文，沉淀结构化页面与章节切片"""
    folder = _paper_folder(paper_id)
    pdf_path = folder / "source.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # 触发 PDF 解析
    parsed = pdf_reader.parse_pdf(pdf_bytes)
    extracted_path = folder / "extracted.json"
    extracted_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新 Paper 元数据
    paper = get_paper(paper_id) or {}
    paper["has_pdf"] = parsed.get("success", False)
    paper["pdf_pages"] = parsed.get("total_pages", 0)
    paper["pdf_path"] = str(pdf_path)
    paper["pdf_checksum"] = parsed.get("checksum")
    paper["sections"] = parsed.get("sections", [])

    (folder / "metadata.json").write_text(
        json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    safe_id = paper_id.replace("/", "_").replace(":", "_")
    (PAPERS_DIR / f"{safe_id}.json").write_text(
        json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "success": parsed.get("success", False),
        "paper_id": paper_id,
        "total_pages": parsed.get("total_pages", 0),
        "word_count": parsed.get("word_count", 0),
        "sections": parsed.get("sections", []),
        "pdf_path": str(pdf_path),
    }


def get_paper_extracted_data(paper_id: str) -> dict[str, Any] | None:
    """获取论文全文解析与切片结构"""
    folder = _paper_folder(paper_id)
    extracted_p = folder / "extracted.json"
    if not extracted_p.exists():
        return None
    try:
        return json.loads(extracted_p.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_paper_evidence_slice(
    project_id: str,
    paper_id: str,
    page: int,
    section: str,
    paragraph_index: int,
    text: str,
    claim: str | None = None,
    hypothesis_id: str | None = None,
) -> dict[str, Any]:
    """将 PDF 原文中的精确段落提取并沉淀为 Evidence 切片"""
    p = get_paper(paper_id)
    title = p.get("title", "Paper") if p else "Paper"

    evidence_id = f"ev_pdf_{int(time.time()*1000)}"
    slice_record = {
        "id": evidence_id,
        "type": "paper",
        "source_type": "paper",
        "source_id": paper_id,
        "paper_id": paper_id,
        "paper_title": title,
        "page": page,
        "section": section,
        "paragraph_index": paragraph_index,
        "source_location": f"Page {page} · {section} · Para #{paragraph_index}",
        "snippet": text.strip(),
        "claim": claim or f"来源于文献《{title}》第 {page} 页【{section}】证据",
        "hypothesis_id": hypothesis_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if hypothesis_id:
        try:
            from backend.domain.hypothesis import get_hypothesis, _save_hypothesis
            h = get_hypothesis(hypothesis_id)
            if h:
                h.setdefault("evidence", []).append(slice_record)
                _save_hypothesis(h)
        except Exception:
            pass
    return slice_record


def ask_paper_question(paper_id: str, question: str) -> dict[str, Any]:
    """对已导入 PDF 的论文进行深度文献事实问答与切片定位"""
    extracted = get_paper_extracted_data(paper_id)
    if not extracted or not extracted.get("success"):
        return {
            "found": False,
            "answer": "该文献尚未导入或解析 PDF 全文，请先上传 PDF 文件以开启全文深度问答与切片提取。",
            "citations": [],
        }

    return pdf_reader.ask_paper(extracted, question)


def list_project_papers(project_id: str) -> list[dict[str, Any]]:
    """列出 Project 下保存的所有文献"""
    from backend.domain.project import get_project
    proj = get_project(project_id)
    if not proj:
        return []

    paper_ids = proj.get("paper_ids", [])
    results = []
    for pid in paper_ids:
        p = get_paper(pid)
        if p:
            results.append(p)
    return results


def get_paper(paper_id: str) -> dict[str, Any] | None:
    """获取单篇保存的文献详情"""
    p = _paper_meta_path(paper_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_paper_from_project(project_id: str, paper_id: str) -> bool:
    """从 Project 中移除保存的文献"""
    from backend.domain.project import get_project, update_project
    proj = get_project(project_id)
    if proj:
        current_papers = list(proj.get("paper_ids", []))
        if paper_id in current_papers:
            current_papers.remove(paper_id)
            update_project(project_id, {"paper_ids": current_papers})

    p = _paper_meta_path(paper_id)
    if p.exists():
        p.unlink()
        return True
    return False
