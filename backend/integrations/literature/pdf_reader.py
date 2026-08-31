"""
PDF Reader & Deep Paper Reading Engine — 本地 PDF 解析与证据切片提取
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _detect_section(text_line: str) -> Optional[str]:
    """启发式识别学术论文常见章节标题"""
    line = text_line.strip()
    patterns = [
        r"^(?:[0-9IVX]+\.?\s*)?(abstract|introduction|related work|background|methodology|method|approach|experiment|experiments|results|discussion|conclusion|limitations|references|datasets?)\b",
    ]
    for p in patterns:
        m = re.match(p, line, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
    return None


class PDFReader:
    """轻量、高效的本地学术 PDF 解析引擎"""

    def parse_pdf(self, pdf_input: str | Path | bytes) -> dict[str, Any]:
        """
        解析 PDF，提取页面、章节与段落切片
        返回结构：
        {
            "success": True,
            "total_pages": N,
            "word_count": M,
            "checksum": "...",
            "pages": [
                {
                    "page_num": 1,
                    "text": "...",
                    "paragraphs": [
                        {"paragraph_index": 0, "section": "Abstract", "text": "..."}
                    ]
                }
            ],
            "sections": ["Abstract", "Introduction", "Method", "Experiments", "Conclusion"]
        }
        """
        try:
            import pypdf
        except ImportError:
            return {"success": False, "error": "pypdf 未安装", "pages": [], "total_pages": 0}

        if isinstance(pdf_input, (str, Path)):
            p = Path(pdf_input).resolve()
            if not p.exists():
                return {"success": False, "error": f"PDF 文件不存在: {pdf_input}", "pages": [], "total_pages": 0}
            pdf_bytes = p.read_bytes()
        else:
            pdf_bytes = pdf_input

        checksum = hashlib.md5(pdf_bytes).hexdigest()

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            pages_data = []
            all_sections = set()
            total_words = 0
            current_section = "Main"

            for page_idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                lines = raw_text.splitlines()
                
                paragraphs = []
                current_p_lines = []
                p_idx = 0

                for line in lines:
                    line_str = line.strip()
                    if not line_str:
                        if current_p_lines:
                            p_text = " ".join(current_p_lines)
                            total_words += len(p_text.split())
                            paragraphs.append({
                                "paragraph_index": p_idx,
                                "section": current_section,
                                "text": p_text,
                            })
                            p_idx += 1
                            current_p_lines = []
                        continue

                    sec = _detect_section(line_str)
                    if sec:
                        current_section = sec
                        all_sections.add(sec)

                    current_p_lines.append(line_str)

                if current_p_lines:
                    p_text = " ".join(current_p_lines)
                    total_words += len(p_text.split())
                    paragraphs.append({
                        "paragraph_index": p_idx,
                        "section": current_section,
                        "text": p_text,
                    })

                pages_data.append({
                    "page_num": page_idx,
                    "text": raw_text,
                    "paragraphs": paragraphs,
                })

            return {
                "success": True,
                "total_pages": total_pages,
                "word_count": total_words,
                "checksum": checksum,
                "pages": pages_data,
                "sections": sorted(list(all_sections)) or ["General"],
            }
        except Exception as e:
            logger.error("PDF parsing failed: %s", e)
            return {"success": False, "error": f"PDF 解析异常: {str(e)}", "pages": [], "total_pages": 0}

    def search_passages(self, parsed_data: dict, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """在解析后的 PDF 内容中按关键词匹配最相关的切片段落"""
        if not parsed_data.get("success"):
            return []

        q_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        if not q_terms:
            return []

        candidates = []
        for page in parsed_data.get("pages", []):
            page_num = page["page_num"]
            for p in page.get("paragraphs", []):
                p_text = p.get("text", "")
                p_lower = p_text.lower()
                
                score = sum(p_lower.count(term) for term in q_terms)
                if score > 0:
                    candidates.append({
                        "page_num": page_num,
                        "section": p.get("section", "General"),
                        "paragraph_index": p.get("paragraph_index", 0),
                        "text": p_text,
                        "score": score,
                    })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    def ask_paper(self, parsed_data: dict, question: str) -> dict[str, Any]:
        """对论文内容执行问答，返回严谨的事实解答与 Evidence 切片定位"""
        passages = self.search_passages(parsed_data, question, top_k=3)
        if not passages:
            return {
                "found": False,
                "answer": "在论文原文中未检索到与该问题直接相关的段落依据 (Not found in source)。",
                "citations": [],
            }

        citations = []
        for p in passages:
            citations.append({
                "page": p["page_num"],
                "section": p["section"],
                "paragraph_index": p["paragraph_index"],
                "snippet": p["text"][:160] + "...",
            })

        # 尝试调用 LLM 总结，未配置时使用确定性摘要
        from src.llm_client import LLMClient
        llm = LLMClient.from_env()
        if llm.is_configured:
            context_str = "\n\n".join([f"[Page {p['page_num']}, {p['section']}] {p['text']}" for p in passages])
            prompt = (
                f"你是一位严谨的科研助手。请基于以下论文原文片段回答科研问题：'{question}'。\n\n"
                f"要求：\n1. 只能根据提供的片段回答，不得臆造外部信息；\n2. 回答后必须显式标注引用出处 (例如: [Page X · Section Y])。\n\n"
                f"论文片段：\n{context_str}"
            )
            raw_ans = llm.call_llm(prompt)
            if not raw_ans.startswith("LLM_"):
                return {
                    "found": True,
                    "answer": raw_ans,
                    "citations": citations,
                }

        # 确定性精准提取响应
        best_p = passages[0]
        summary_ans = f"根据论文第 {best_p['page_num']} 页【{best_p['section']}】章节内容：\n\"{best_p['text'][:240]}...\""
        return {
            "found": True,
            "answer": summary_ans,
            "citations": citations,
        }


pdf_reader = PDFReader()
