import math

import pytest

from ragdocs.index import BM25Index, _chunk_texts, build_index, load_index, save_index
from ragdocs.ingest import Chunk


def make_chunks():
    return [
        Chunk("pets.md", "Feeding cats", "feeding-cats", 2, "Cats eat twice a day."),
        Chunk("pets.md", "Walking dogs", "walking-dogs", 2, "Dogs need a daily walk."),
        Chunk("cars.md", "Changing oil", "changing-oil", 2, "Change engine oil yearly."),
    ]


def test_tfidf_round_trip(tmp_path):
    index = build_index(make_chunks(), "tfidf")
    save_index(index, tmp_path / "idx")
    loaded = load_index(tmp_path / "idx")

    results = loaded.search("when do cats eat", k=2)
    top_chunk, top_score = results[0]
    assert top_chunk.heading == "Feeding cats"
    assert top_score > 0
    assert len(loaded.chunks) == 3


def make_fruit_chunks():
    return [
        Chunk("fruit.md", "Apples", "apples", 2, "Apples are crisp and apples keep for weeks."),
        Chunk(
            "fruit.md",
            "Orchard",
            "orchard",
            2,
            "The orchard grows apples, pears, plums, cherries and quinces in long rows.",
        ),
        Chunk("fruit.md", "Pears", "pears", 2, "Pears ripen off the tree."),
        Chunk("fruit.md", "Storage", "storage", 2, "Keep fruit cool."),
    ]


def okapi_bm25(query: list[str], docs: list[list[str]], k1=1.5, b=0.75) -> list[float]:
    """Okapi BM25 written out term by term, as a reference for the vectorized index."""
    avgdl = sum(len(doc) for doc in docs) / len(docs)
    scores = []
    for doc in docs:
        score = 0.0
        for term in query:
            df = sum(term in d for d in docs)
            idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
            tf = doc.count(term)
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(doc) / avgdl))
        scores.append(score)
    return scores


def test_bm25_ranks_toy_corpus():
    index = build_index(make_fruit_chunks(), "bm25")

    def headings(query):
        return [chunk.heading for chunk, _ in index.search(query, k=4)]

    # Three mentions in a short chunk beat one in a long chunk; the two chunks
    # without the term tie at zero and keep corpus order.
    assert headings("apples") == ["Apples", "Orchard", "Pears", "Storage"]
    assert headings("pears")[:2] == ["Pears", "Orchard"]
    # Matching both query terms once beats matching one of them twice.
    assert headings("pears plums")[0] == "Orchard"


def test_bm25_scores_match_okapi_formula():
    chunks = make_fruit_chunks()
    index = build_index(chunks, "bm25")
    analyze = index.vectorizer.build_analyzer()
    docs = [analyze(text) for text in _chunk_texts(chunks)]

    for query in ["apples", "pears plums", "apples apples orchard", "bananas"]:
        reference = okapi_bm25(analyze(query), docs)
        expected = {chunk.chunk_id: score for chunk, score in zip(chunks, reference, strict=True)}
        scores = {chunk.chunk_id: score for chunk, score in index.search(query, k=len(chunks))}
        assert scores == pytest.approx(expected)


def test_bm25_round_trip(tmp_path):
    index = build_index(make_chunks(), "bm25")
    save_index(index, tmp_path / "idx")
    loaded = load_index(tmp_path / "idx")

    assert isinstance(loaded, BM25Index)
    original = [(chunk.chunk_id, score) for chunk, score in index.search("when do cats eat", k=3)]
    reloaded = [(chunk.chunk_id, score) for chunk, score in loaded.search("when do cats eat", k=3)]
    assert reloaded == original
    assert original[0][0] == "pets.md#feeding-cats"
