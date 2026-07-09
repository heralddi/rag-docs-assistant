# Tax

Meridian calculates tax on invoices automatically once you tell it where you are registered to collect. Tax is computed at [invoice finalization](invoices.md#finalize-an-invoice) using the customer's billing address and tax IDs.

## Tax registrations

A tax registration declares that your business collects tax in a jurisdiction. Without a registration for the customer's jurisdiction, invoices to that customer carry zero tax.

`POST /v1/tax_registrations`

| Parameter | Required | Description |
|---|---|---|
| `country` | yes | Two-letter ISO 3166-1 code, for example `DE`. |
| `state` | conditional | Required for countries with subnational tax, such as `US` and `CA`. |
| `type` | yes | Registration kind, for example `eu_vat`, `us_sales_tax`, `gb_vat`. |
| `effective_from` | no | Date the registration takes effect. Defaults to today. |

```json
{
  "id": "txr_7hN3sVp1",
  "object": "tax_registration",
  "country": "DE",
  "type": "eu_vat",
  "effective_from": "2026-01-01",
  "livemode": false
}
```

## How tax is calculated

At finalization, Meridian determines the jurisdiction from the customer's billing country and state, checks for an active registration, applies the current rate for each line item's product category, and writes the result to the invoice's `tax` field with a per-line breakdown. Rates are maintained by Meridian and updated as law changes; you do not enter percentages.

The calculation is a snapshot. Later rate changes never alter a finalized invoice, and corrections flow through [credit notes](credit-notes.md).

## Customer tax IDs

A validated business tax ID can change the treatment of a transaction, for example zero-rating an EU cross-border sale under the reverse-charge mechanism. Add IDs on the [customer](customers.md#the-customer-object) as `tax_ids`:

| Field | Description |
|---|---|
| `type` | ID scheme, for example `eu_vat`, `gb_vat`, `us_ein`. |
| `value` | The identifier itself, for example `DE811907980`. |

EU VAT IDs are validated against VIES asynchronously. Until validation completes, tax is calculated as if the ID were absent, and the invoice is corrected with a credit note if validation later succeeds within the same billing period.

## Reading tax on an invoice

The invoice `tax` field holds the total. Each line carries its own breakdown:

```json
{
  "description": "Team plan, 3 seats, Jun 1 to Jul 1",
  "amount": 8700,
  "tax_amounts": [
    { "rate": 0.19, "jurisdiction": "DE", "amount": 1653 }
  ]
}
```

Amounts are in the smallest currency unit and rounded per line, half up. Sum `tax_amounts` across lines to reconcile with the invoice `tax` total.
