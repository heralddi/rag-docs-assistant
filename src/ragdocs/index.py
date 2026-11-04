"""Build, persist, and query retrieval indexes over documentation chunks."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np

from .ingest import Chunk

DEFAULT_INDEX_DIR = Path(".ragdocs_index")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BACKENDS = ("embed", "tfidf", "bm25")


def _chunk_texts(chunks: list[Chunk]) -> list[str]:
    """The text that gets vectorized: heading plus body."""
    return [f"{c.heading}\n{c.text}" for c in chunks]


def _save_chunks(chunks: list[Chunk], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(dataclasses.asdict(chunk)) + "\n")


def _load_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f]


class EmbedIndex:
    """Dense retrieval: MiniLM sentence embeddings, cosine similarity."""

    backend = "embed"

    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, model=None):
        self.chunks = chunks
        self.embeddings = embeddings  # unit-normalized, shape (n_chunks, dim)
        self._model = model

    @classmethod
    def build(cls, chunks: list[Chunk]) -> EmbedIndex:
        model = _load_embed_model()
        embeddings = model.encode(
            _chunk_texts(chunks), normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)
        return cls(chunks, embeddings, model)

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        if self._model is None:
            self._model = _load_embed_model()
        query_vec = self._model.encode([query], normalize_embeddings=True)[0]
        scores = self.embeddings @ query_vec
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]

    def save(self, index_dir: Path) -> None:
        np.save(index_dir / "embeddings.npy", self.embeddings)

    @classmethod
    def load(cls, index_dir: Path, chunks: list[Chunk]) -> EmbedIndex:
        return cls(chunks, np.load(index_dir / "embeddings.npy"))


class TfidfIndex:
    """Sparse retrieval: TF-IDF over unigrams and bigrams, cosine similarity."""

    backend = "tfidf"

    def __init__(self, chunks: list[Chunk], vectorizer, matrix):
        self.chunks = chunks
        self.vectorizer = vectorizer
        self.matrix = matrix  # L2-normalized sparse matrix, (n_chunks, vocab)

    @classmethod
    def build(cls, chunks: list[Chunk]) -> TfidfIndex:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(_chunk_texts(chunks))
        return cls(chunks, vectorizer, matrix)

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        query_vec = self.vectorizer.transform([query])
        scores = (self.matrix @ query_vec.T).toarray().ravel()
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]

    def save(self, index_dir: Path) -> None:
        import joblib
        from scipy import sparse

        joblib.dump(self.vectorizer, index_dir / "vectorizer.joblib")
        sparse.save_npz(index_dir / "matrix.npz", self.matrix)

    @classmethod
    def load(cls, index_dir: Path, chunks: list[Chunk]) -> TfidfIndex:
        import joblib
        from scipy import sparse

        vectorizer = joblib.load(index_dir / "vectorizer.joblib")
        matrix = sparse.load_npz(index_dir / "matrix.npz")
        return cls(chunks, vectorizer, matrix)


def _bm25_weights(counts, k1: float, b: float):
    """Okapi BM25 weight of every (chunk, term) pair in a sparse count matrix.

    weight = idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl)), where
    idf = log(1 + (N - df + 0.5) / (df + 0.5)), dl is the chunk's length in
    indexed tokens (after stop-word removal), and avgdl is the mean of dl.
    """
    from scipy import sparse

    counts = sparse.coo_matrix(counts, dtype=np.float64)
    n_chunks, n_terms = counts.shape
    doc_len = np.asarray(counts.sum(axis=1)).ravel()
    df = np.bincount(counts.col, minlength=n_terms)
    idf = np.log1p((n_chunks - df + 0.5) / (df + 0.5))
    tf = counts.data
    length_norm = k1 * (1 - b + b * doc_len[counts.row] / doc_len.mean())
    weights = idf[counts.col] * tf * (k1 + 1) / (tf + length_norm)
    return sparse.csr_matrix((weights, (counts.row, counts.col)), shape=counts.shape)


class BM25Index:
    """Sparse retrieval: Okapi BM25 over unigram counts, k1 = 1.5 and b = 0.75.

    Tokenization, lowercasing, and stop words are the same as the tfidf
    backend. A chunk's score is the sum of its BM25 weights over the query's
    terms, counted as often as they occur in the query.
    """

    backend = "bm25"
    k1 = 1.5
    b = 0.75

    def __init__(self, chunks: list[Chunk], vectorizer, matrix):
        self.chunks = chunks
        self.vectorizer = vectorizer
        self.matrix = matrix  # BM25 term weights, sparse (n_chunks, vocab)

    @classmethod
    def build(cls, chunks: list[Chunk]) -> BM25Index:
        from sklearn.feature_extraction.text import CountVectorizer

        vectorizer = CountVectorizer(stop_words="english")
        counts = vectorizer.fit_transform(_chunk_texts(chunks))
        return cls(chunks, vectorizer, _bm25_weights(counts, cls.k1, cls.b))

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        query_counts = self.vectorizer.transform([query])
        scores = (self.matrix @ query_counts.T).toarray().ravel()
        # BM25 gives exact ties to chunks that match the same terms equally often
        # and have the same length; a stable sort keeps them in corpus order.
        top = np.argsort(-scores, kind="stable")[:k]
        return [(self.chunks[i], float(scores[i])) for i in top]

    def save(self, index_dir: Path) -> None:
        import joblib
        from scipy import sparse

        joblib.dump(self.vectorizer, index_dir / "bm25_vectorizer.joblib")
        sparse.save_npz(index_dir / "bm25_weights.npz", self.matrix)

    @classmethod
    def load(cls, index_dir: Path, chunks: list[Chunk]) -> BM25Index:
        import joblib
        from scipy import sparse

        vectorizer = joblib.load(index_dir / "bm25_vectorizer.joblib")
        matrix = sparse.load_npz(index_dir / "bm25_weights.npz")
        return cls(chunks, vectorizer, matrix)


_BACKEND_CLASSES = {"embed": EmbedIndex, "tfidf": TfidfIndex, "bm25": BM25Index}


def _load_embed_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def build_index(chunks: list[Chunk], backend: str) -> EmbedIndex | TfidfIndex | BM25Index:
    if backend not in _BACKEND_CLASSES:
        raise ValueError(f"Unknown backend {backend!r}, expected one of {BACKENDS}")
    return _BACKEND_CLASSES[backend].build(chunks)


def save_index(
    index: EmbedIndex | TfidfIndex | BM25Index, index_dir: str | Path = DEFAULT_INDEX_DIR
) -> None:
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    _save_chunks(index.chunks, index_dir / "chunks.jsonl")
    (index_dir / "meta.json").write_text(
        json.dumps({"backend": index.backend, "num_chunks": len(index.chunks)}, indent=2)
    )
    index.save(index_dir)


def load_index(index_dir: str | Path = DEFAULT_INDEX_DIR) -> EmbedIndex | TfidfIndex | BM25Index:
    index_dir = Path(index_dir)
    meta_path = index_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"No index found at {index_dir}. Build one first: python -m ragdocs index"
        )
    meta = json.loads(meta_path.read_text())
    chunks = _load_chunks(index_dir / "chunks.jsonl")
    return _BACKEND_CLASSES[meta["backend"]].load(index_dir, chunks)
