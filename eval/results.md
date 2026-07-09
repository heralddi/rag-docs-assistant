# Retrieval benchmark results

30 questions, gold = source file plus heading, candidates ranked at k=10.

| Backend | hit@1 | hit@3 | MRR@10 |
|---|---|---|---|
| embed | 0.767 | 0.900 | 0.841 |
| tfidf | 0.533 | 0.833 | 0.698 |

Questions where the gold section was not ranked first:

- (embed) How do I paginate through all results from a list endpoint?
- (embed) What is the maximum page size for list endpoints?
- (embed) What happens when I exceed the rate limit?
- (embed) How do I verify the signature on a webhook delivery?
- (embed) What happens when I issue a credit note against an invoice that was already paid?
- (embed) Why do my invoices show zero tax?
- (embed) What changed in API version 2026-05-01?
- (tfidf) How do I paginate through all results from a list endpoint?
- (tfidf) What is the maximum page size for list endpoints?
- (tfidf) What are restricted API keys and when should I use them?
- (tfidf) Which errors are safe to retry automatically?
- (tfidf) What happens when I exceed the rate limit?
- (tfidf) How do I verify the signature on a webhook delivery?
- (tfidf) How long are failed webhook deliveries retried?
- (tfidf) How do I register a new webhook endpoint?
- (tfidf) Why does deleting a customer return a 409?
- (tfidf) Why is there a delay before subscription invoices are finalized?
- (tfidf) What does finalizing an invoice actually do?
- (tfidf) What happens when I issue a credit note against an invoice that was already paid?
- (tfidf) What changed in API version 2026-05-01?
- (tfidf) How do I report metered usage for a subscription item?
