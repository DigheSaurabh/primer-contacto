# Schema (v1)

## Form A: New request (one per request, under 2 minutes)
| # | Field | Type | Options or rule |
|---|---|---|---|
| 1 | `request_id` | Short text (auto-suggested) | Date plus a letter, e.g. `2026-10-22-A` |
| 2 | `received_at` | Date and time | When the request arrived, not when it was logged |
| 3 | `channel` | Single choice | Instagram DM; Linktree form; text message; email; phone call; in person; referral; other |
| 4 | `request_type` | Single choice | Private session; small group; corporate session; school event; community event; workshop; class series; other |
| 5 | `language` | Single choice | English; Spanish; both; other |
| 6 | `client_type` | Single choice | Individual; company; school; nonprofit or community organization; studio; other |
| 7 | `event_zip` | Short text, optional | ZIP code of the event only, never a street address |
| 8 | `quoted_amount` | Number, optional | USD, once a quote exists |
| 9 | `note` | Long text, optional | What they asked for. No names, handles or phone numbers |

## Form B: Stage update (one per movement, under 30 seconds)
| # | Field | Type | Options or rule |
|---|---|---|---|
| 10 | `request_id` | Short text | Must match Form A |
| 11 | `stage` | Single choice | Replied; Quoted; Confirmed; Delivered; Invoiced; Paid; Lost |
| 12 | `stage_at` | Date and time | When it happened |
| 13 | `lost_reason` | Single choice, shown if Lost | No reply from client; declined price; scheduling conflict; went elsewhere; cancelled; other |
| 14 | `update_note` | Long text, optional | No names |

Computed by the app (not entered): 15 `outcome` (open; delivered and paid; lost), 16 `last_stage`.

## CSV: wide format (booking-tool exports and spreadsheets)
One row per request. Only `request_id`, `received_at` and `channel` are required.

| Column | Type | Notes |
|---|---|---|
| `request_id` | text | Required, unique |
| `received_at` | datetime | Required |
| `channel` | text | Required, mapped to the Form A list |
| `request_type`, `language`, `client_type`, `event_zip` | text | Optional |
| `replied_at`, `quoted_at`, `confirmed_at`, `delivered_at`, `invoiced_at`, `paid_at` | datetime | Optional; blank means the stage was not reached |
| `lost_at`, `lost_reason` | datetime, text | Optional |
| `quoted_amount` | number | Optional, USD |
| `note` | text | Optional; the app warns if it looks like it contains names or emails |

## CSV: long format (what the metrics read)
One row per stage reached: `request_id`, `stage`, `stage_at`, plus Form A attributes joined on `request_id`. Built by `transform.py`.

## Validation rules (Week 2, `validate.py`)
- Required columns present
- Dates in order: received ≤ replied ≤ quoted ≤ confirmed ≤ delivered ≤ invoiced ≤ paid
- No stage recorded after `lost_at`
- `request_id` unique
- Completeness report: % filled per column
