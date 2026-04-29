# Zod parity follow-ups

The `check-zod-parity.sh` PostToolUse hook compares fields declared in `backend/app/schemas/*.py` to fields in the matching `src/lib/api/schemas/<stem>.ts`. Anything in the Pydantic schema but missing from Zod is silently dropped at parse time — Zod's default `z.object()` strips unknowns.

Survey run on 2026-04-29 against all 22 backend schema files identified four files with real drift. `deal.ts` was partially fixed (12 `DealResponse` fields added); the rest are tracked here.

## Priority 1 — `property.ts`

37 missing fields. `property.py` is the largest schema and most likely to be silently dropping data the UI needs.

Missing (first 10): `acquisition_date, address, avg_rent_per_sf, avg_rent_per_unit, cap_rate, city, county, current_value, data_source, description` — plus 27 more.

To do:
1. Read both `backend/app/schemas/property.py` and `src/lib/api/schemas/property.ts`.
2. Identify which Pydantic class each missing field belongs to (likely `PropertyResponse` vs `PropertyCreate`/`PropertyUpdate`/sub-classes).
3. Add the response-only fields to the Zod input shape with `.nullable().optional()` per CLAUDE.md convention.
4. Run `npm run test:run -- src/features/property` to confirm no regressions.

## Priority 2 — `reporting.ts`

43+ missing fields. Likely a mix of report config schemas, scheduled report fields, and template metadata.

Missing (first 10): `category, completed_at, config, configurable, created_at, created_by, day_of_month, day_of_week, default_height, default_width` — plus 33 more.

Approach: same as property.ts. Reporting code is newer (recently shipped — see commit `6cbc6a3 feat(reports)`) so the gap may reflect intentional separation between backend admin schemas and frontend wire schemas. Verify before adding fields wholesale.

## Priority 3 — `construction.ts`

5 missing fields: `count, results, rows_imported, rows_updated, total_value`.

Small and tractable. These look like batch-import response fields — confirm whether the frontend triggers construction imports and needs the result stats.

## Priority 4 — `deal.ts` sub-class artifacts

23 fields the hook flags on `deal.py` are NOT `DealResponse` fields — they belong to sibling response classes that have no Zod schema at all:

- `ProformaFieldValue`, `ProformaFieldGroup`, `ProformaReturnsResponse` — `category`, `field_name`, `fields`, `groups`, `value_numeric`, `value_text`
- `WatchlistStatusResponse` — `is_watched`
- `StageChangeLogResponse`, `StageHistoryResponse` — `changed_by_user_id`, `history`, `new_stage`, `old_stage`, `reason`
- `KanbanBoardResponse` — `stage_counts`, `stages`, `total_deals`
- `StageMappingResponse` — `folder_to_stage`
- `DealCursorPaginatedResponse` — `has_more`, `next_cursor`, `prev_cursor`
- `DealListResponse` — `items`, `page`, `page_size` (already covered partially via `dealsListResponseSchema`)
- Shared — `deal_id`, `deal_name`, `total`

If the frontend calls the corresponding endpoints (`/deals/{id}/proforma-returns`, `/deals/{id}/watchlist`, `/deals/{id}/stage-history`, `/deals/kanban`, etc.), each needs its own Zod schema. If those endpoints are unused, the noise can be silenced by extending `check-zod-parity.sh` to scope to a single Pydantic class.

## Hook limitation

`check-zod-parity.sh` is regex-based: it grabs every indented `name: type` line in the `.py` file and checks against every Zod field in the `.ts` file, with no awareness of Pydantic class boundaries. That's why a single-file Pydantic module with 8 response classes generates noise like the deal.py case above. A future iteration could parse the AST (via Python `ast` module) and emit one diff per class — out of scope for now, but logged here.
