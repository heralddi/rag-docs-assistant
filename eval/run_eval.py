"""Retrieval benchmark: hit@1, hit@3, and MRR@10 per backend, with paired tests.

Usage: python eval/run_eval.py [--docs DIR] [--questions FILE] [--backends embed tfidf bm25]
Writes eval/results.json and eval/results.md. A backend left out of --backends keeps
its per-question ranks from the existing eval/results.json, so the embed results can
be reported without downloading the model. Every statistic is computed from the
per-question ranks.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np

from ragdocs.index import BACKENDS, EMBED_MODEL, build_index
from ragdocs.ingest import Chunk, chunk_directory

EVAL_DIR = Path(__file__).parent
TOP_K = 10
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 0
Z_95 = NormalDist().inv_cdf(0.975)


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


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, 95% by default."""
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def bootstrap_mean_interval(
    values: list[float], resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED
) -> tuple[float, float]:
    """95% percentile bootstrap interval for a mean, resampling questions with replacement."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(values), size=(resamples, len(values)))
    low, high = np.percentile(values[samples].mean(axis=1), [2.5, 97.5])
    return float(low), float(high)


def binomial_two_sided_p(k: int, n: int) -> float:
    """Exact two-sided binomial test of k successes in n trials against p = 0.5."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(k, n - k) + 1)) / 2**n
    return min(1.0, 2 * tail)


def reciprocal_ranks(ranks: list[int | None]) -> list[float]:
    """1 / rank per question, 0 when the gold section is not in the top k."""
    return [1 / r if r else 0.0 for r in ranks]


def evaluate_backend(backend: str, chunks: list[Chunk], questions: list[dict]) -> dict:
    index = build_index(chunks, backend)
    per_question = []
    for question in questions:
        results = index.search(question["question"], k=TOP_K)
        rank = gold_rank(results, question)
        per_question.append(
            {
                "question": question["question"],
                "gold_rank": rank,
                "top_ids": [chunk.chunk_id for chunk, _ in results],
            }
        )
    entry = {"backend": backend}
    if backend == "embed":
        entry["model"] = EMBED_MODEL
    return {**entry, "from_stored_run": False, "per_question": per_question}


def load_stored_results(path: Path) -> dict[str, dict]:
    """Backend entries of an existing results.json, keyed by backend name."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["backends"] if isinstance(data, dict) else data  # older files: a bare list
    return {entry["backend"]: entry for entry in entries}


def stored_entry(entry: dict, questions: list[dict]) -> dict:
    """A stored entry's per-question ranks, checked against the current questions."""
    backend = entry["backend"]
    if [p["question"] for p in entry["per_question"]] != [q["question"] for q in questions]:
        raise ValueError(
            f"Stored {backend} results are for a different question set; "
            f"re-run them with --backends {backend}"
        )
    kept = {"backend": backend}
    if backend == "embed":
        # results.json files written before the model name was recorded all used EMBED_MODEL.
        kept["model"] = entry.get("model", EMBED_MODEL)
    return {**kept, "from_stored_run": True, "per_question": entry["per_question"]}


def summarize(entry: dict) -> dict:
    """Add hit@1, hit@3, MRR@10 and their 95% intervals, computed from the gold ranks."""
    ranks = [p["gold_rank"] for p in entry["per_question"]]
    n = len(ranks)
    hits1 = sum(r == 1 for r in ranks if r)
    hits3 = sum(r <= 3 for r in ranks if r)
    rr = reciprocal_ranks(ranks)
    info = {key: value for key, value in entry.items() if key != "per_question"}
    return {
        **info,
        "num_questions": n,
        "hit@1": hits1 / n,
        "hit@1_ci95": wilson_interval(hits1, n),
        "hit@3": hits3 / n,
        "hit@3_ci95": wilson_interval(hits3, n),
        f"mrr@{TOP_K}": sum(rr) / n,
        f"mrr@{TOP_K}_ci95": bootstrap_mean_interval(rr),
        "per_question": entry["per_question"],
    }


def paired_comparison(a: dict, b: dict) -> dict:
    """Exact McNemar test on hit@1 and exact sign test on reciprocal rank, same questions."""
    ranks_a = [p["gold_rank"] for p in a["per_question"]]
    ranks_b = [p["gold_rank"] for p in b["per_question"]]
    pairs = list(zip(ranks_a, ranks_b, strict=True))
    only_a = sum(ra == 1 and rb != 1 for ra, rb in pairs)
    only_b = sum(rb == 1 and ra != 1 for ra, rb in pairs)
    rr_pairs = list(zip(reciprocal_ranks(ranks_a), reciprocal_ranks(ranks_b), strict=True))
    higher_a = sum(x > y for x, y in rr_pairs)
    higher_b = sum(x < y for x, y in rr_pairs)
    return {
        "a": a["backend"],
        "b": b["backend"],
        "hit@1_only_a": only_a,
        "hit@1_only_b": only_b,
        "mcnemar_exact_p": binomial_two_sided_p(only_a, only_a + only_b),
        "rr_higher_a": higher_a,
        "rr_higher_b": higher_b,
        "rr_tied": len(rr_pairs) - higher_a - higher_b,
        "sign_test_exact_p": binomial_two_sided_p(higher_a, higher_a + higher_b),
    }


def same_file_outranks(entry: dict, questions: list[dict]) -> tuple[int, int]:
    """Misses where a section of the gold file ranks above the gold section, and all misses.

    Needs the stored top-k lists.
    """
    outranked = misses = 0
    for question, p in zip(questions, entry["per_question"], strict=True):
        if p["gold_rank"] == 1:
            continue
        misses += 1
        above = p["top_ids"][: (p["gold_rank"] or TOP_K + 1) - 1]
        outranked += any(chunk_id.startswith(question["source_file"] + "#") for chunk_id in above)
    return outranked, misses


def _label(entry: dict) -> str:
    notes = [entry["model"].split("/")[-1]] if "model" in entry else []
    if entry["from_stored_run"]:
        notes.append("stored run")
    return f"{entry['backend']} ({', '.join(notes)})" if notes else entry["backend"]


def _with_interval(entry: dict, metric: str) -> str:
    low, high = entry[f"{metric}_ci95"]
    return f"{entry[metric]:.3f} [{low:.3f}, {high:.3f}]"


def _p_value(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def write_markdown(results: dict, questions: list[dict], path: Path) -> None:
    entries = results["backends"]
    lines = [
        "# Retrieval benchmark results",
        "",
        f"{results['num_questions']} questions, gold = source file plus heading, "
        f"candidates ranked at k={TOP_K}. Brackets give 95% intervals: Wilson score intervals "
        f"for hit@1 and hit@3, and a percentile bootstrap over questions for MRR@{TOP_K} "
        f"({BOOTSTRAP_RESAMPLES:,} resamples, seed {BOOTSTRAP_SEED}).",
        "",
        f"| Backend | hit@1 | hit@3 | MRR@{TOP_K} |",
        "|---|---|---|---|",
    ]
    for e in entries:
        lines.append(
            f"| {_label(e)} | {_with_interval(e, 'hit@1')} | {_with_interval(e, 'hit@3')} "
            f"| {_with_interval(e, f'mrr@{TOP_K}')} |"
        )
    for e in entries:
        if e["from_stored_run"]:
            model = f" with {e['model'].split('/')[-1]}" if "model" in e else ""
            lines += [
                "",
                f"The {e['backend']} row is computed from the per-question ranks of a stored "
                f"run{model}; that backend was not re-run.",
            ]
    if results["paired_comparisons"]:
        lines += [
            "",
            "Paired comparisons on the same questions. For hit@1, the counts are the questions "
            "where only one backend ranks the gold section first (exact McNemar test). For "
            "reciprocal rank (RR), they are the questions where one backend ranks the gold "
            "section higher (exact sign test, ties dropped). p-values are two-sided and not "
            "adjusted for multiple comparisons.",
            "",
            "| A vs B | hit@1 only A / only B | McNemar p | RR higher A / B / tied | Sign test p |",
            "|---|---|---|---|---|",
        ]
        for c in results["paired_comparisons"]:
            lines.append(
                f"| {c['a']} vs {c['b']} | {c['hit@1_only_a']} / {c['hit@1_only_b']} "
                f"| {_p_value(c['mcnemar_exact_p'])} "
                f"| {c['rr_higher_a']} / {c['rr_higher_b']} / {c['rr_tied']} "
                f"| {_p_value(c['sign_test_exact_p'])} |"
            )
    rows = []
    for i, p in enumerate(entries[0]["per_question"]):
        ranks = [e["per_question"][i]["gold_rank"] for e in entries]
        if any(r != 1 for r in ranks):
            rows.append(f"| {p['question']} | " + " | ".join(str(r or "-") for r in ranks) + " |")
    if rows:
        lines += [
            "",
            "Questions where at least one backend did not rank the gold section first, with the "
            f"gold rank per backend (- = not in the top {TOP_K}):",
            "",
            "| Question | " + " | ".join(e["backend"] for e in entries) + " |",
            "|---|" + "---|" * len(entries),
            *rows,
        ]
    outranked = [
        (e["backend"], *same_file_outranks(e, questions))
        for e in entries
        if all("top_ids" in p for p in e["per_question"])
    ]
    if outranked:
        lines += [
            "",
            "Misses where a section from the gold section's own file ranks above it: "
            + ", ".join(f"{backend} {k} of {n}" for backend, k, n in outranked)
            + ".",
        ]
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

    results_path = EVAL_DIR / "results.json"
    stored = load_stored_results(results_path)
    entries = []
    for backend in BACKENDS:
        if backend in args.backends:
            print(f"Evaluating backend: {backend} ({len(questions)} questions)")
            entry = summarize(evaluate_backend(backend, chunks, questions))
        elif backend in stored:
            print(f"Keeping stored per-question ranks for backend: {backend}")
            entry = summarize(stored_entry(stored[backend], questions))
        else:
            continue
        print(
            f"  hit@1={entry['hit@1']:.3f}  hit@3={entry['hit@3']:.3f}  "
            f"mrr@{TOP_K}={entry[f'mrr@{TOP_K}']:.3f}"
        )
        entries.append(entry)

    results = {
        "num_questions": len(questions),
        "top_k": TOP_K,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "backends": entries,
        "paired_comparisons": [
            paired_comparison(a, b) for a, b in itertools.combinations(entries, 2)
        ],
    }
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_markdown(results, questions, EVAL_DIR / "results.md")
    print(f"Wrote {results_path} and {EVAL_DIR / 'results.md'}")


if __name__ == "__main__":
    main()
