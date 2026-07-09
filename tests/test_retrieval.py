from pathlib import Path

import pytest

from ragdocs.answer import format_extractive
from ragdocs.index import build_index
from ragdocs.ingest import chunk_directory

DOCS_DIR = Path(__file__).parents[1] / "data" / "sample_docs"


@pytest.fixture(scope="module")
def tfidf_index():
    return build_index(chunk_directory(DOCS_DIR), "tfidf")


def test_pagination_question_retrieves_pagination_doc(tfidf_index):
    results = tfidf_index.search("How do I paginate list endpoints?", k=3)
    assert any(chunk.source_file == "pagination.md" for chunk, _ in results)


def test_extractive_answer_cites_sources(tfidf_index):
    results = tfidf_index.search("How do I verify a webhook signature?", k=3)
    text = format_extractive("How do I verify a webhook signature?", results)
    top_chunk, _ = results[0]
    assert top_chunk.citation in text
    assert top_chunk.text in text  # verbatim passage, not a paraphrase
