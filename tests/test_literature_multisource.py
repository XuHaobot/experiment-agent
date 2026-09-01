"""
Unit Tests for Multi-Source Literature Providers & Direct Ingestion
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.integrations.literature.bibtex_parser import parse_bibtex
from backend.integrations.literature.dblp import DBLPProvider
from backend.integrations.literature.crossref import CrossRefProvider
from backend.integrations.literature.pubmed import PubMedProvider
from backend.integrations.literature import search_literature, get_literature_provider


def test_bibtex_parser():
    raw_bibtex = """
    @article{vaswani2017attention,
      title={Attention is all you need},
      author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N and Kaiser, {\\L}ukasz and Polosukhin, Illia},
      journal={Advances in neural information processing systems},
      volume={30},
      year={2017},
      doi={10.48550/arXiv.1706.03762}
    }
    """
    papers = parse_bibtex(raw_bibtex)
    assert len(papers) == 1
    p = papers[0]
    assert "Attention is all you need" in p.title
    assert "Vaswani" in p.authors[0]
    assert p.year == 2017
    assert p.doi == "10.48550/arXiv.1706.03762"
    assert p.source == "bibtex"


def test_provider_registration():
    for name in ["openalex", "arxiv", "semantic_scholar", "pubmed", "dblp", "crossref"]:
        prov = get_literature_provider(name)
        assert prov is not None
        assert prov.name == name


def test_crossref_doi_lookup():
    cr = CrossRefProvider()
    paper = cr.get_paper("10.1145/3326362")
    if paper:
        assert "Dynamic Graph" in paper.title or "10.1145/3326362" in paper.doi
