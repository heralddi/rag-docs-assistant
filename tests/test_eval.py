import sys
from pathlib import Path

from ragdocs.ingest import chunk_directory

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "eval"))

from run_eval import load_questions, validate_gold  # noqa: E402


def test_benchmark_questions_load_and_gold_targets_exist():
    questions = load_questions(REPO_ROOT / "eval" / "questions.jsonl")
    assert len(questions) == 30
    assert all({"question", "source_file", "heading"} <= q.keys() for q in questions)
    chunks = chunk_directory(REPO_ROOT / "data" / "sample_docs")
    validate_gold(questions, chunks)  # raises on any dangling gold target
