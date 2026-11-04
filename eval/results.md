# Retrieval benchmark results

30 questions, gold = source file plus heading, candidates ranked at k=10. Brackets give 95% intervals: Wilson score intervals for hit@1 and hit@3, and a percentile bootstrap over questions for MRR@10 (10,000 resamples, seed 0).

| Backend | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| embed (all-MiniLM-L6-v2, stored run) | 0.767 [0.591, 0.882] | 0.900 [0.744, 0.965] | 0.841 [0.729, 0.939] |
| tfidf | 0.533 [0.361, 0.698] | 0.833 [0.664, 0.927] | 0.698 [0.574, 0.815] |
| bm25 | 0.633 [0.455, 0.781] | 0.900 [0.744, 0.965] | 0.759 [0.638, 0.872] |

The embed row is computed from the per-question ranks of a stored run with all-MiniLM-L6-v2; that backend was not re-run.

Paired comparisons on the same questions. For hit@1, the counts are the questions where only one backend ranks the gold section first (exact McNemar test). For reciprocal rank (RR), they are the questions where one backend ranks the gold section higher (exact sign test, ties dropped). p-values are two-sided and not adjusted for multiple comparisons.

| A vs B | hit@1 only A / only B | McNemar p | RR higher A / B / tied | Sign test p |
|---|---|---|---|---|
| embed vs tfidf | 8 / 1 | 0.039 | 11 / 2 / 17 | 0.022 |
| embed vs bm25 | 6 / 2 | 0.289 | 9 / 4 / 17 | 0.267 |
| tfidf vs bm25 | 1 / 4 | 0.375 | 2 / 8 / 20 | 0.109 |

Questions where at least one backend did not rank the gold section first, with the gold rank per backend (- = not in the top 10):

| Question | embed | tfidf | bm25 |
|---|---|---|---|
| How do I paginate through all results from a list endpoint? | 7 | - | - |
| What is the maximum page size for list endpoints? | 2 | 4 | 4 |
| What are restricted API keys and when should I use them? | 1 | 2 | 1 |
| Which header carries the API key on each request? | 1 | 1 | 3 |
| Which errors are safe to retry automatically? | 1 | 4 | 3 |
| What happens when I exceed the rate limit? | 2 | 3 | 3 |
| How do I verify the signature on a webhook delivery? | 2 | 2 | 1 |
| How long are failed webhook deliveries retried? | 1 | 5 | 2 |
| How do I register a new webhook endpoint? | 1 | 2 | 1 |
| Why does deleting a customer return a 409? | 1 | 4 | 3 |
| Why is there a delay before subscription invoices are finalized? | 1 | 2 | 1 |
| What does finalizing an invoice actually do? | 1 | 2 | 2 |
| What happens when I issue a credit note against an invoice that was already paid? | 3 | 3 | 2 |
| Why do my invoices show zero tax? | 6 | 1 | 1 |
| What changed in API version 2026-05-01? | 10 | 2 | 2 |
| How do I report metered usage for a subscription item? | 1 | 3 | 5 |

Misses where a section from the gold section's own file ranks above it: tfidf 9 of 14, bm25 7 of 11.
