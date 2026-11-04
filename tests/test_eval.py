import itertools
import json
import sys
from pathlib import Path

import pytest
from scipy.stats import binomtest

from ragdocs.ingest import chunk_directory

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "eval"))

from question_overlap import heading_overlap  # noqa: E402
from run_eval import (  # noqa: E402
    Z_95,
    binomial_two_sided_p,
    bootstrap_mean_interval,
    evaluate_backend,
    load_questions,
    load_stored_results,
    paired_comparison,
    stored_entry,
    summarize,
    validate_gold,
    wilson_interval,
)


def test_benchmark_questions_load_and_gold_targets_exist():
    questions = load_questions(REPO_ROOT / "eval" / "questions.jsonl")
    assert len(questions) == 30
    assert all({"question", "source_file", "heading"} <= q.keys() for q in questions)
    chunks = chunk_directory(REPO_ROOT / "data" / "sample_docs")
    validate_gold(questions, chunks)  # raises on any dangling gold target


def test_stored_results_follow_from_their_per_question_ranks():
    questions = load_questions(REPO_ROOT / "eval" / "questions.jsonl")
    chunks = chunk_directory(REPO_ROOT / "data" / "sample_docs")
    results = json.loads((REPO_ROOT / "eval" / "results.json").read_text(encoding="utf-8"))
    entries = results["backends"]
    assert [e["backend"] for e in entries] == ["embed", "tfidf", "bm25"]
    for entry in entries:
        assert [p["question"] for p in entry["per_question"]] == [q["question"] for q in questions]
        assert json.loads(json.dumps(summarize(entry))) == entry
        if entry["backend"] != "embed":  # the sparse backends must reproduce exactly
            rerun = evaluate_backend(entry["backend"], chunks, questions)
            assert rerun["per_question"] == entry["per_question"]
    pairs = [paired_comparison(a, b) for a, b in itertools.combinations(entries, 2)]
    assert results["paired_comparisons"] == pairs


def test_older_results_format_and_question_mismatch(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps([{"backend": "embed", "per_question": []}]), encoding="utf-8")
    assert load_stored_results(path) == {"embed": {"backend": "embed", "per_question": []}}
    assert load_stored_results(tmp_path / "missing.json") == {}

    entry = {"backend": "embed", "per_question": [{"question": "Old?", "gold_rank": 1}]}
    with pytest.raises(ValueError, match="different question set"):
        stored_entry(entry, [{"question": "New?"}])


def test_wilson_interval():
    low, high = wilson_interval(0, 30)
    assert low == pytest.approx(0.0, abs=1e-12)
    assert high == pytest.approx(Z_95**2 / (30 + Z_95**2))
    scipy_ci = binomtest(23, 30).proportion_ci(confidence_level=0.95, method="wilson")
    assert wilson_interval(23, 30) == pytest.approx((scipy_ci.low, scipy_ci.high))
    low, high = wilson_interval(7, 30)
    assert wilson_interval(23, 30) == pytest.approx((1 - high, 1 - low))


def test_binomial_two_sided_p():
    assert binomial_two_sided_p(0, 5) == 2 / 32
    assert binomial_two_sided_p(1, 9) == 20 / 512
    assert binomial_two_sided_p(3, 6) == 1.0
    assert binomial_two_sided_p(0, 0) == 1.0
    for n in range(1, 21):
        for k in range(n + 1):
            assert binomial_two_sided_p(k, n) == pytest.approx(binomtest(k, n).pvalue)


def test_bootstrap_mean_interval_is_seeded():
    values = [1.0, 0.5, 0.0, 1.0, 0.25, 1.0, 0.0, 0.5]
    low, high = bootstrap_mean_interval(values)
    assert (low, high) == bootstrap_mean_interval(values)
    assert low < sum(values) / len(values) < high
    assert bootstrap_mean_interval([0.5] * 10) == (0.5, 0.5)


def test_paired_comparison():
    ranks_a = [1, 1, 1, 1, 1, 2, None, 1, 3]
    ranks_b = [2, 3, None, 4, 5, 2, None, 1, 1]
    a = {"backend": "a", "per_question": [{"gold_rank": r} for r in ranks_a]}
    b = {"backend": "b", "per_question": [{"gold_rank": r} for r in ranks_b]}
    result = paired_comparison(a, b)
    assert (result["hit@1_only_a"], result["hit@1_only_b"]) == (5, 1)
    assert result["mcnemar_exact_p"] == 14 / 64
    assert (result["rr_higher_a"], result["rr_higher_b"], result["rr_tied"]) == (5, 1, 3)
    assert result["sign_test_exact_p"] == 14 / 64


def test_heading_overlap_counts_exact_content_words():
    rotate = {"question": "How do I rotate an API key?", "heading": "Rotating keys"}
    assert heading_overlap(rotate) == ({"rotating", "keys"}, set())
    restricted = {"question": "What are restricted API keys?", "heading": "Restricted keys"}
    assert heading_overlap(restricted) == ({"restricted", "keys"}, {"restricted", "keys"})
