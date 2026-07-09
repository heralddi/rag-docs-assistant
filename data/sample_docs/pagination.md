# Pagination

All list endpoints share one cursor-based pagination scheme. List endpoints never return every object at once; they return one page and a cursor for fetching the next.

## The list envelope

Every list response has the same shape:

```json
{
  "object": "list",
  "data": [
    { "id": "inv_8kQ2mVx", "object": "invoice", "...": "..." },
    { "id": "inv_7pL9nRw", "object": "invoice", "...": "..." }
  ],
  "has_more": true,
  "url": "/v1/invoices"
}
```

| Field | Type | Description |
|---|---|---|
| `data` | array | The objects on this page, newest first. |
| `has_more` | boolean | Whether more objects exist beyond this page. |
| `url` | string | The endpoint that produced the list. |

## Pagination parameters

Every list endpoint accepts the same three query parameters:

| Parameter | Type | Description |
|---|---|---|
| `limit` | integer | Page size, 1 to 100. Defaults to 25. |
| `starting_after` | string | An object ID. Returns objects created before it in list order, that is, the next page when reading newest to oldest. |
| `ending_before` | string | An object ID. Returns objects created after it, for paging backwards. |

Pass at most one of `starting_after` and `ending_before`. Sending both returns a `parameter_invalid` error.

## Iterating through all pages

To walk an entire collection, request a page, then pass the ID of the last object in `data` as `starting_after` until `has_more` is `false`:

```bash
curl "https://api.meridianbilling.com/v1/invoices?limit=100" \
  -H "Authorization: Bearer mb_test_51hGx..."

curl "https://api.meridianbilling.com/v1/invoices?limit=100&starting_after=inv_7pL9nRw" \
  -H "Authorization: Bearer mb_test_51hGx..."
```

Use `limit=100` for bulk reads to minimize round trips and stay well inside your [rate limits](rate-limits.md).

## Cursor stability

Cursors are plain object IDs, so pagination is stable under concurrent writes: objects created while you iterate appear before your starting point and are simply not visited, and deleting the cursor object invalidates that cursor with a `404`. If you need a consistent snapshot, filter by a fixed `created` range:

```
GET /v1/invoices?created_lte=2026-06-01T00:00:00Z&limit=100
```

## Filtering and list order

List endpoints return objects newest first by creation time. There is no `sort` parameter. Endpoint-specific filters, such as `status` on invoices or `customer` on subscriptions, combine freely with pagination parameters and are documented on each endpoint page.
