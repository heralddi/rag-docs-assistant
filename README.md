# rag-docs-assistant

[![CI](https://github.com/heralddi/rag-docs-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/heralddi/rag-docs-assistant/actions/workflows/ci.yml)

A question-answering tool for API documentation. Given a question, it finds the documentation section that answers it and, by default, quotes that section verbatim, cited as `[file § heading]`. An optional generative mode synthesizes a cited answer from the retrieved sections instead. Retrieval uses sentence embeddings with cosine search, with TF-IDF and BM25 baselines for comparison, and all three backends are measured on a 30-question retrieval benchmark.

I write API documentation for a living. This project is the other side of that work: if docs are structured well, a small retrieval system should be able to find the right section for a real question. The corpus here is an original, fictional "Meridian Billing API" documentation set I wrote for this repo, so it doubles as a writing sample.

## How it works

```
data/sample_docs/*.md
        |
        v
ingest.py    splits each file into chunks at every heading;
             each chunk keeps its source file and heading anchor
        |
        v
index.py     three interchangeable backends:
             embed  = all-MiniLM-L6-v2 sentence embeddings + cosine similarity (numpy)
             tfidf  = scikit-learn TfidfVectorizer, unigrams and bigrams
             bm25   = Okapi BM25 over CountVectorizer unigrams, k1 = 1.5, b = 0.75
             each one persists to .ragdocs_index/
        |
        v
answer.py    retrieves top-k chunks and returns the best passage verbatim,
             cited as [source_file § heading]; optional generative mode
             synthesizes an answer through an OpenAI-compatible API
```

The default answer mode is extractive. The system quotes the retrieved passage instead of generating text, so the answer can never say something the docs do not say. Generative mode is opt-in and grounded in the same retrieved chunks.

The bm25 backend follows Robertson and Zaragoza (2009), with the idf variant log(1 + (N - df + 0.5) / (df + 0.5)) and the same tokenizer and stop-word list as tfidf.

## Quickstart

Requires Python 3.12 or newer. The first `index` run downloads the embedding model (about 90 MB) from Hugging Face. Clone the repo, then from its root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m ragdocs index --docs data/sample_docs --backend embed
python -m ragdocs ask "How do I paginate list endpoints?"
```

Example output:

```
Q: How do I paginate list endpoints?

Best passage [pagination.md § Pagination]:

All list endpoints share one cursor-based pagination scheme. List endpoints never
return every object at once; they return one page and a cursor for fetching the next.

Other relevant sections:
  2. [pagination.md § Pagination parameters] (score 0.659)
  3. [pagination.md § Filtering and list order] (score 0.529)
```

To index your own documentation, point `--docs` at any directory of markdown files:

```bash
python -m ragdocs index --docs path/to/your/docs --backend embed
```

Use `--backend tfidf` or `--backend bm25` for a dependency-light index that needs no model download.

### Generative mode (optional)

If `OPENAI_API_KEY` is set, `--mode generative` sends the retrieved chunks to a chat completions endpoint and asks for a synthesized answer that cites them. `OPENAI_BASE_URL` and `OPENAI_MODEL` override the defaults, so any OpenAI-compatible server works. Without a key the command explains why and falls back to the extractive answer.

```bash
python -m ragdocs ask "When should I use a credit note?" --mode generative
```

## Evaluation

`eval/questions.jsonl` holds 30 questions I wrote against the sample corpus. Each question has a gold answer location, defined as a source file plus heading. `eval/run_eval.py` builds each index, retrieves 10 candidates per question, and scores the rank of the gold section.

Results with 95% intervals (Wilson score for hit rates, percentile bootstrap over questions with 10,000 resamples for MRR):

| Backend | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| embed (all-MiniLM-L6-v2) | 0.767 [0.591, 0.882] | 0.900 [0.744, 0.965] | 0.841 [0.729, 0.939] |
| tfidf | 0.533 [0.361, 0.698] | 0.833 [0.664, 0.927] | 0.698 [0.574, 0.815] |
| bm25 | 0.633 [0.455, 0.781] | 0.900 [0.744, 0.965] | 0.759 [0.638, 0.872] |

The embed row is computed from per-question ranks stored by an earlier run with all-MiniLM-L6-v2. `python eval/run_eval.py --backends tfidf bm25` re-runs the other two backends and keeps that entry.

In paired tests, embed ranks the gold section first on 8 questions where tfidf does not, against 1 the other way (exact McNemar test, p = 0.039; exact sign test on reciprocal rank, p = 0.022). The hit@1 splits for embed against bm25 and bm25 against tfidf are 6 to 2 and 4 to 1 (McNemar p = 0.289 and 0.375). No p-value stays below 0.05 after a Bonferroni correction for the three pairs.

Per-question ranks, top-10 section ids for tfidf and bm25, and all paired tests are in `eval/results.json` and `eval/results.md`. In 9 of the 14 tfidf misses and 7 of the 11 bm25 misses, another section of the same file outranked the gold section.

## The sample corpus

`data/sample_docs/` documents a fictional Meridian Billing API: 15 pages covering authentication, errors, rate limits, pagination, webhooks, six resource endpoints, a changelog, and two task guides. All of it is original text written for this repo. Any resemblance to a real billing product's docs is a matter of genre conventions.

## Running the tests

```bash
python -m pytest
```

The suite covers the chunker, index persistence and round-trip, BM25 scoring, the CLI, retrieval sanity on the sample corpus, the evaluation statistics, and benchmark integrity.

## Limitations

- The corpus is small, 15 files and 93 chunks. Scores on a corpus this size say little about how the same pipeline would rank sections in a large documentation set.
- I wrote both the docs and the benchmark questions, so the questions inevitably share vocabulary with the sections that answer them: 19 of the 30 questions contain at least one content word of their gold heading, and 18 contain at least half of them (exact word forms after stop-word removal, `eval/question_overlap.py`). Numbers would be lower with questions from real users.
- Each question has a single gold section, so ranking another section that also answers it counts as a miss.
- The default answer is extractive. It returns the best section, not a synthesized answer, and a question whose answer spans two sections gets only the better one quoted.
- Chunking is purely heading-based. A very long section becomes one very long chunk.

## References

- Robertson, S. & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in Information Retrieval 3(4), 333-389.

## License

MIT. See [LICENSE](LICENSE).
