# Rate limits

The API applies rate limits per account and per environment. Limits exist to keep the platform stable for everyone; well-behaved integrations rarely hit them.

## Default limits

| Environment | Sustained rate | Burst allowance |
|---|---|---|
| Live | 100 requests per second | 200 requests in any 1-second window |
| Test | 25 requests per second | 50 requests in any 1-second window |

Read and write requests share the same budget. If your integration needs a higher sustained limit, contact support with your account ID and expected peak rate.

## Rate limit headers

Every response includes three headers describing the current window:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1767427205
```

| Header | Description |
|---|---|
| `X-RateLimit-Limit` | Your sustained requests-per-second limit. |
| `X-RateLimit-Remaining` | Requests left in the current window. |
| `X-RateLimit-Reset` | Unix timestamp when the window resets. |

## When you are rate limited

Requests over the limit return `429 Too Many Requests` with the error code `rate_limited` and a `Retry-After` header giving the number of seconds to wait:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 2
```

The request was not processed. It is always safe to retry a rate-limited request.

## Retrying safely

Use exponential backoff with jitter, seeded from `Retry-After` when present:

1. Wait `Retry-After` seconds, or 1 second if the header is absent.
2. On each subsequent failure, double the wait and add random jitter of up to 50 percent.
3. Cap the wait at 32 seconds and give up after 6 attempts, then alert.

Reuse the original `Idempotency-Key` on every retry of a `POST` so a request that actually succeeded is not applied twice. See [Idempotent requests](overview.md#idempotent-requests).

## Reducing your request volume

- Prefer [webhooks](webhooks.md) over polling. Polling list endpoints for changes is the most common cause of rate limiting.
- Use `limit=100` when walking a collection instead of the default page size. See [Pagination](pagination.md).
- Cache objects that change rarely, such as prices and tax registrations.
