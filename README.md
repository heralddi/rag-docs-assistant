# rag-docs-assistant

[![CI](https://github.com/heralddi/rag-docs-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/heralddi/rag-docs-assistant/actions/workflows/ci.yml)

A retrieval-augmented documentation assistant. It answers questions over a set of API docs and cites the exact section every answer comes from. Retrieval uses sentence embeddings with cosine search, with a TF-IDF baseline for comparison, and both backends are measured on a 30-question retrieval benchmark.

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
index.py     two interchangeable backends:
             embed  = all-MiniLM-L6-v2 sentence embeddings + cosine similarity (numpy)
             tfidf  = scikit-learn TfidfVectorizer, unigrams and bigrams
             either one persists to .ragdocs_index/
        |
        v
answer.py    retrieves top-k chunks and returns the best passage verbatim,
             cited as [source_file § heading]; optional generative mode
             synthesizes an answer through an OpenAI-compatible API
```

The default answer mode is extractive. The system quotes the retrieved passage instead of generating text, so the answer can never say something the docs do not say. Generative mode is opt-in and grounded in the same retrieved chunks.

## Quickstart

Requires Python 3.10 or newer. The first `index` run downloads the embedding model (about 90 MB) from Hugging Face. Clone the repo, then from its root:

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

Use `--backend tfidf` for a dependency-light index that needs no model download.

### Generative mode (optional)

If `OPENAI_API_KEY` is set, `--mode generative` sends the retrieved chunks to a chat completions endpoint and asks for a synthesized answer that cites them. `OPENAI_BASE_URL` and `OPENAI_MODEL` override the defaults, so any OpenAI-compatible server works. Without a key the command explains why and falls back to the extractive answer.

```bash
python -m ragdocs ask "When should I use a credit note?" --mode generative
```

## Evaluation

`eval/questions.jsonl` holds 30 questions I wrote against the sample corpus. Each question has a gold answer location, defined as a source file plus heading. `eval/run_eval.py` builds both indexes, retrieves 10 candidates per question, and scores the rank of the gold section.

Results from running `python eval/run_eval.py` on this corpus:

| Backend | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| embed (all-MiniLM-L6-v2) | 0.767 | 0.900 | 0.841 |
| tfidf | 0.533 | 0.833 | 0.698 |

The per-question ranks and the list of misses are in `eval/results.json` and `eval/results.md`. Most misses are near-misses where a sibling section of the same file outranked the gold section.

## The sample corpus

`data/sample_docs/` documents a fictional Meridian Billing API: 15 pages covering authentication, errors, rate limits, pagination, webhooks, six resource endpoints, a changelog, and two task guides. All of it is original text written for this repo. Any resemblance to a real billing product's docs is a matter of genre conventions.

## Running the tests

```bash
python -m pytest
```

The suite covers the chunker, index persistence and round-trip, retrieval sanity on the sample corpus, and benchmark integrity.

## Limitations

- The corpus is small, 15 files and 93 chunks. Scores on a corpus this size say little about how the same pipeline would rank sections in a large documentation set.
- I wrote both the docs and the benchmark questions, so the questions inevitably share vocabulary with the sections that answer them. Numbers would be lower with questions from real users.
- The default answer is extractive. It returns the best section, not a synthesized answer, and a question whose answer spans two sections gets only the better one quoted.
- Chunking is purely heading-based. A very long section becomes one very long chunk.

## License

MIT. See [LICENSE](LICENSE).
