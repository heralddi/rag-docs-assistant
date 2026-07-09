"""Retrieval benchmark: hit@1, hit@3, and MRR@10 for both backends.

Usage: python eval/run_eval.py [--docs DIR] [--questions FILE] [--backends embed tfidf]
Writes eval/results.json and eval/results.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ragdocs.index import BACKENDS, build_index
from ragdocs.ingest import Chunk, chunk_directory

EVAL_DIR = Path(__file__).parent
TOP_K = 10


def load_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate_gold(questions: list[dict], chunks: list[Chunk]) -> None:
    """Every gold (file, heading) pair must name a real chunk."""
    known = {(c.source_file, c.heading) for c in chunks}
    missing = [q for q in questions if (q["source_file"], q["heading"]) not in known]
    if missing:
        listing = ", ".join(f"{q['source_file']} | {q['heading']}" for q in missing)
        raise ValueError(f"Gold targets not found in corpus: {listing}")


def gold_rank(results: list[tuple[Chunk, float]], question: dict) -> int | None:
    """1-based rank of the gold chunk in the results, or None if absent."""
    for rank, (chunk, _) in enumerate(results, start=1):
        if chunk.source_file == question["source_file"] and chunk.heading == question["heading"]:
            return rank
    return None


def evaluate_backend(backend: str, chunks: list[Chunk], questions: list[dict]) -> dict:
    index = build_index(chunks, backend)
    per_question = []
    for question in questions:
        results = index.search(question["question"], k=TOP_K)
        rank = gold_rank(results, question)
        per_question.append({"question": question["question"], "gold_rank": rank})
    n = len(questions)
    ranks = [p["gold_rank"] for p in per_question]
    return {
        "backend": backend,
        "num_questions": n,
        "hit@1": sum(r == 1 for r in ranks if r) / n,
        "hit@3": sum(r <= 3 for r in ranks if r) / n,
        f"mrr@{TOP_K}": sum(1 / r for r in ranks if r) / n,
        "per_question": per_question,
    }


def write_markdown(results: list[dict], path: Path) -> None:
    lines = [
        "# Retrieval benchmark results",
        "",
        f"{results[0]['num_questions']} questions, gold = source file plus heading, "
        f"candidates ranked at k={TOP_K}.",
        "",
        f"| Backend | hit@1 | hit@3 | MRR@{TOP_K} |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['backend']} | {r['hit@1']:.3f} | {r['hit@3']:.3f} | {r[f'mrr@{TOP_K}']:.3f} |"
        )
    misses = [
        (r["backend"], p["question"])
        for r in results
        for p in r["per_question"]
        if p["gold_rank"] != 1
    ]
    if misses:
        lines += ["", "Questions where the gold section was not ranked first:", ""]
        lines += [f"- ({backend}) {question}" for backend, question in misses]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", default="data/sample_docs")
    parser.add_argument("--questions", default=str(EVAL_DIR / "questions.jsonl"))
    parser.add_argument("--backends", nargs="+", choices=BACKENDS, default=list(BACKENDS))
    args = parser.parse_args()

    chunks = chunk_directory(args.docs)
    questions = load_questions(Path(args.questions))
    validate_gold(questions, chunks)

    results = []
    for backend in args.backends:
        print(f"Evaluating backend: {backend} ({len(questions)} questions)")
        result = evaluate_backend(backend, chunks, questions)
        print(
            f"  hit@1={result['hit@1']:.3f}  hit@3={result['hit@3']:.3f}  "
            f"mrr@{TOP_K}={result[f'mrr@{TOP_K}']:.3f}"
        )
        results.append(result)

    (EVAL_DIR / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_markdown(results, EVAL_DIR / "results.md")
    print(f"Wrote {EVAL_DIR / 'results.json'} and {EVAL_DIR / 'results.md'}")


if __name__ == "__main__":
    main()
