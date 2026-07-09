# Meridian Billing API overview

The Meridian Billing API is a REST API for managing the full billing lifecycle: customers, subscriptions, invoices, payments, credit notes, and tax. All requests and responses use JSON. The API is organized around predictable resource URLs and standard HTTP verbs.

Base URL:

```
https://api.meridianbilling.com/v1
```

## Environments

Meridian provides two fully separated environments.

| Environment | Key prefix | Purpose |
|---|---|---|
| Live | `mb_live_` | Real customers, real money movement |
| Test | `mb_test_` | Integration development, no money movement |

Test mode mirrors live mode exactly, including webhooks and error behavior. Objects created in test mode never appear in live mode, and test API keys cannot read live data. See [Authentication](authentication.md) for how keys work.

## Request format

Send request bodies as JSON with the `Content-Type: application/json` header. All timestamps are ISO 8601 strings in UTC, for example `2026-05-14T09:30:00Z`. Monetary amounts are integers in the smallest currency unit (cents for USD, yen for JPY) paired with an ISO 4217 `currency` code.

```bash
curl https://api.meridianbilling.com/v1/customers \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{"email": "ada@example.com", "name": "Ada Lovelace"}'
```

## API versioning

The API is versioned by date. Pin a version by sending the `Meridian-Version` header:

```
Meridian-Version: 2026-05-01
```

If you omit the header, requests use the version that was current when your account was created. New dated versions are announced in the [changelog](changelog.md) at least 30 days before older versions enter the deprecation window. Breaking changes only ship in new dated versions.

## Core objects

| Object | ID prefix | Description |
|---|---|---|
| Customer | `cus_` | A person or company you bill |
| Subscription | `sub_` | A recurring billing agreement for a customer |
| Price | `prc_` | A reusable amount and billing interval |
| Invoice | `inv_` | A statement of amounts owed, drawn from subscriptions or created directly |
| Payment | `pay_` | An attempt to collect an invoice balance |
| Credit note | `cn_` | A correction that reduces an invoice amount |
| Event | `evt_` | A record of something that happened, delivered by webhooks |

Every object has a unique ID with the prefix shown above, a `created` timestamp, and a `livemode` boolean.

## Idempotent requests

Every `POST` request accepts an `Idempotency-Key` header. If a request with the same key is retried within 24 hours, the API returns the result of the original request instead of performing the operation again. Use a random UUID per logical operation.

```
Idempotency-Key: 7f2b9c4e-1a83-4c6d-9e5f-0b12d34a56c7
```

Idempotency keys are scoped to your account and to the endpoint path. Retrying with the same key but a different request body returns an `idempotency_key_reused` error. See [Errors](errors.md).

## Where to go next

- [Authentication](authentication.md) explains API keys and key rotation.
- [Pagination](pagination.md) covers cursor pagination for all list endpoints.
- [Webhooks](webhooks.md) covers event delivery and signature verification.
- The guide [Setting up usage-based billing](setting-up-usage-based-billing.md) walks through a complete integration.
