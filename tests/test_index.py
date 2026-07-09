from ragdocs.index import build_index, load_index, save_index
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
