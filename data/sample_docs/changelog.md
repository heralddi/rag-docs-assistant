# Changelog

Dated API versions are listed newest first. Pin a version with the `Meridian-Version` header as described in [API versioning](overview.md#api-versioning). Versions marked deprecated continue to work for 12 months after the deprecation notice.

## 2026-05-01

- Added the `paused` subscription status with `POST /v1/subscriptions/{id}/pause` and `/resume`. In earlier versions, pausing required canceling and recreating the subscription.
- The invoice object now includes a per-line `tax_amounts` breakdown. Previously only the invoice-level `tax` total was exposed.
- Webhook signing moved from the `v0` scheme to `v1` (timestamped HMAC-SHA256). `v0` signatures stopped being sent for endpoints created after this version. See [Verifying signatures](webhooks.md#verifying-signatures).
- Breaking: `DELETE /v1/customers/{id}` now returns `409` with code `customer_has_activity` when the customer has open invoices. Previously it silently voided them.

## 2025-11-15

- Added restricted API keys with per-resource permissions. See [Restricted keys](authentication.md#restricted-keys).
- Added `ending_before` for backwards pagination on all list endpoints.
- Raised the maximum `limit` on list endpoints from 50 to 100.
- Breaking: monetary amounts on payments moved from decimal strings to integer minor units, matching invoices.

## 2025-06-20

- Initial public release: customers, subscriptions, invoices, payments, credit notes, tax registrations, webhooks.
- Deprecated: the private beta endpoints under `/v0` stopped accepting new accounts. Beta accounts have until 2026-06-20 to migrate.
