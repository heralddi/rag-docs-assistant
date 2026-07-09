# Authentication

The Meridian Billing API authenticates every request with an API key sent as a bearer token. Requests without a valid key return `401 Unauthorized`.

```
Authorization: Bearer mb_live_51hGx9TQe...
```

All requests must use HTTPS. Requests made over plain HTTP are rejected before authentication with a `400 Bad Request` and are never redirected, so a key sent over HTTP is not replayed.

## API key types

| Key type | Prefix | Access |
|---|---|---|
| Live secret key | `mb_live_` | Full read and write access to live data |
| Test secret key | `mb_test_` | Full read and write access to test data |
| Restricted key | `mb_rk_` | Access limited to the permissions you select |

Secret keys grant full account access. Treat them like passwords: store them in a secrets manager, never commit them to source control, and never expose them in client-side code.

## Restricted keys

Restricted keys carry an explicit permission set per resource: `none`, `read`, or `write`. Use them for services that only need partial access. A reporting service, for example, needs `read` on invoices and payments and `none` on everything else.

Create restricted keys in the Dashboard under Developers, then API keys. A restricted key used outside its permission set returns a `403 Forbidden` with the error code `permission_denied`, and the `error.message` names the missing permission.

## Rotating keys

Rotate a key whenever it may have been exposed, and on a regular schedule as a matter of hygiene. Rotation is a two-step process designed for zero downtime:

1. In the Dashboard, choose Roll key. This issues a replacement key immediately and puts the old key into a grace period you select, from 1 hour up to 72 hours.
2. Deploy the new key to your services. When the grace period ends, the old key stops working.

During the grace period both keys authenticate, so a fleet of servers can be updated gradually. Requests made with an expired key return `401 Unauthorized` with the code `api_key_expired`.

## Machine-to-machine checklist

- Send the key only in the `Authorization` header, never in the URL or request body.
- Use a restricted key with the smallest permission set that works.
- Pin a `Meridian-Version` so key rotation and API upgrades stay independent. See [API versioning](overview.md#api-versioning).
- Alert on spikes of `401` responses in production. They usually mean a rotation was not fully deployed.
