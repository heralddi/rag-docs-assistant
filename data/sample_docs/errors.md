# Errors

The Meridian Billing API uses conventional HTTP status codes and returns a structured error body with every non-2xx response. Client errors (4xx) indicate a problem with the request. Server errors (5xx) indicate a problem on Meridian's side and are safe to retry with an idempotency key.

## Error response body

Every error response has a single top-level `error` object:

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "parameter_missing",
    "message": "Missing required parameter: customer.",
    "param": "customer",
    "request_id": "req_9f3KzT2mQ"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Broad category. One of `invalid_request_error`, `authentication_error`, `permission_error`, `rate_limit_error`, `payment_error`, `api_error`. |
| `code` | string | Stable machine-readable identifier for the specific failure. |
| `message` | string | Human-readable explanation. Content may change; do not parse it. |
| `param` | string | The request parameter at fault, when one applies. Otherwise absent. |
| `request_id` | string | Unique ID for this request. Include it in support tickets. |

Branch on `type` and `code`, never on `message`.

## HTTP status codes

| Status | Meaning |
|---|---|
| 400 | The request body or query string is malformed or fails validation. |
| 401 | The API key is missing, invalid, or expired. |
| 402 | A payment could not be completed. Inspect `code` for the reason. |
| 403 | The key is valid but lacks permission for this operation. |
| 404 | The resource does not exist, or it exists in the other environment. |
| 409 | The request conflicts with the current state of the resource. |
| 422 | The request is well formed but cannot be processed, for example finalizing an invoice that is already void. |
| 429 | Too many requests. See [Rate limits](rate-limits.md). |
| 500 | Internal error on Meridian's side. Retry with the same idempotency key. |

A `404` in live mode for an object you created in test mode is expected: the two environments share nothing. See [Environments](overview.md#environments).

## Common error codes

| Code | Type | Meaning |
|---|---|---|
| `parameter_missing` | invalid_request_error | A required parameter was not sent. |
| `parameter_invalid` | invalid_request_error | A parameter has the wrong type or an out-of-range value. |
| `idempotency_key_reused` | invalid_request_error | The same `Idempotency-Key` was sent with a different body. |
| `api_key_expired` | authentication_error | The key was rolled and its grace period has ended. |
| `permission_denied` | permission_error | A restricted key lacks the needed permission. |
| `rate_limited` | rate_limit_error | Request rate exceeded. Honor `Retry-After`. |
| `card_declined` | payment_error | The card issuer declined the charge. |
| `insufficient_funds` | payment_error | The payment method has insufficient funds. |

## Handling errors in code

Treat error handling as three tiers:

1. `429` and `5xx`: retry with exponential backoff and the original `Idempotency-Key`. See [Retrying safely](rate-limits.md#retrying-safely).
2. `402` payment errors: do not retry blindly. Route the invoice into your dunning flow. See [Handling failed payments](handling-failed-payments.md).
3. Other `4xx`: fix the request. Log `request_id`, `type`, `code`, and `param`.

## Getting help

When contacting support, include the `request_id` from the error body and the approximate UTC time of the request. Request IDs are retained for 90 days.
