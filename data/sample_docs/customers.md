# Customers

A customer represents a person or company you bill. Subscriptions, invoices, and payments all hang off a customer. Create the customer first; everything else references its ID.

## The customer object

```json
{
  "id": "cus_3nXp7Kd9",
  "object": "customer",
  "email": "ada@example.com",
  "name": "Ada Lovelace",
  "currency": "usd",
  "tax_ids": [{ "type": "eu_vat", "value": "DE811907980" }],
  "metadata": { "crm_id": "8842" },
  "created": "2026-04-11T08:20:31Z",
  "livemode": false
}
```

| Attribute | Type | Description |
|---|---|---|
| `email` | string | Billing email. Receipts and dunning emails go here. |
| `name` | string | Full name or company name, printed on invoices. |
| `currency` | string | ISO 4217 code. Set on first invoice if omitted, then immutable. |
| `tax_ids` | array | Tax identifiers used for invoice compliance. See [Tax](tax.md). |
| `metadata` | object | Up to 50 key-value string pairs for your own bookkeeping. |

## Create a customer

`POST /v1/customers`

| Parameter | Required | Description |
|---|---|---|
| `email` | yes | Must be a valid address. Not required to be unique. |
| `name` | no | Recommended, appears on invoices. |
| `currency` | no | Locks the customer to one currency immediately. |
| `metadata` | no | Key-value strings, 500 characters per value. |

```bash
curl https://api.meridianbilling.com/v1/customers \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{"email": "ada@example.com", "name": "Ada Lovelace", "metadata": {"crm_id": "8842"}}'
```

Duplicate emails are allowed because distinct legal entities can share a billing address. Enforce uniqueness in your own system if you need it, using `metadata` to store your internal key.

## Retrieve a customer

`GET /v1/customers/{id}`

Returns the customer, or `404` if the ID does not exist in the current environment.

## Update a customer

`POST /v1/customers/{id}`

Send only the fields you want to change. Setting a field to `null` clears it. `currency` cannot be changed once set; attempting to returns a `409` with code `currency_locked`.

## List customers

`GET /v1/customers`

Supports the standard [pagination parameters](pagination.md#pagination-parameters) plus:

| Filter | Description |
|---|---|
| `email` | Exact-match filter on email. |
| `created_gte`, `created_lte` | Bound the creation time. |

## Delete a customer

`DELETE /v1/customers/{id}`

Deletion is permanent and only allowed when the customer has no active subscriptions and no open invoices; otherwise the API returns `409` with code `customer_has_activity`. Deleted customers remain readable with `"deleted": true` for audit purposes, but accept no writes.
