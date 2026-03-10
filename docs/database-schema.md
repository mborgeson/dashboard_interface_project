# Database Schema Reference

**Generated: 2026-03-10**
**Database:** PostgreSQL (port 5432) | `dashboard_interface_data`
**ORM:** SQLAlchemy 2.0 async (Mapped/mapped_column style)
**Migrations:** Alembic (`backend/alembic/versions/`)
**Naming convention:** snake_case throughout; constraint naming via `MetaData(naming_convention=...)` in `backend/app/db/base.py`

---

## Table of Contents

1. [Schema Overview](#schema-overview)
2. [Mixins](#mixins)
3. [Core Tables](#core-tables)
4. [Extraction Tables](#extraction-tables)
5. [Underwriting Tables](#underwriting-tables)
6. [Activity and Audit Tables](#activity-and-audit-tables)
7. [Reporting Tables](#reporting-tables)
8. [Construction Pipeline Tables](#construction-pipeline-tables)
9. [Market Data Tables](#market-data-tables)
10. [File Monitoring Tables](#file-monitoring-tables)
11. [Utility Tables](#utility-tables)
12. [Foreign Key Relationships](#foreign-key-relationships)
13. [Index Inventory](#index-inventory)
14. [CHECK Constraint Inventory](#check-constraint-inventory)
15. [Enum Types](#enum-types)
16. [Model vs Live Schema Drift Notes](#model-vs-live-schema-drift-notes)
17. [Migration History](#migration-history)

---

## Schema Overview

| # | Table | PK Type | Mixins | Row Description |
|---|-------|---------|--------|-----------------|
| 1 | `users` | INTEGER | Timestamp, SoftDelete | Dashboard users with JWT auth |
| 2 | `properties` | INTEGER | Timestamp, SoftDelete | Real estate assets |
| 3 | `deals` | INTEGER | Timestamp, SoftDelete | Investment pipeline opportunities |
| 4 | `transactions` | INTEGER | Timestamp, SoftDelete | Financial transactions |
| 5 | `documents` | INTEGER | Timestamp, SoftDelete | Uploaded files and documents |
| 6 | `extraction_runs` | UUID | Timestamp | Batch extraction runs |
| 7 | `extracted_values` | UUID | Timestamp | EAV extracted field values |
| 8 | `underwriting_models` | INTEGER | Timestamp, SoftDelete, SourceTracking | Parent UW analysis entity |
| 9 | `uw_general_assumptions` | INTEGER | Timestamp, SourceTracking | Property basics (32 fields) |
| 10 | `uw_exit_assumptions` | INTEGER | Timestamp, SourceTracking | Exit timing (3 fields) |
| 11 | `uw_noi_assumptions` | INTEGER | Timestamp, SourceTracking | Income/expenses (65+ fields) |
| 12 | `uw_financing_assumptions` | INTEGER | Timestamp, SourceTracking | Debt/equity (53 fields) |
| 13 | `uw_budget_assumptions` | INTEGER | Timestamp, SourceTracking | Acquisition/renovation (32 fields) |
| 14 | `uw_property_returns` | INTEGER | Timestamp, SourceTracking | Property-level returns (44 fields) |
| 15 | `uw_equity_returns` | INTEGER | Timestamp, SourceTracking | LP/GP returns (21 fields) |
| 16 | `uw_unit_mix` | INTEGER | Timestamp, SourceTracking | Per-unit-type rows |
| 17 | `uw_rent_comps` | INTEGER | Timestamp, SourceTracking | Per-comp rent data |
| 18 | `uw_sales_comps` | INTEGER | Timestamp, SourceTracking | Per-comp transaction data |
| 19 | `uw_annual_cashflows` | INTEGER | Timestamp, SourceTracking | Per-year cashflow projections |
| 20 | `property_activities` | INTEGER | Timestamp | Property interaction log |
| 21 | `deal_activities` | INTEGER | Timestamp | Deal interaction log |
| 22 | `user_watchlists` | INTEGER | Timestamp | User deal watchlist |
| 23 | `activity_logs` | UUID | *(custom created_at)* | UUID-based deal audit trail |
| 24 | `audit_logs_admin` | INTEGER | *(custom timestamps)* | Admin action audit trail |
| 25 | `report_settings` | INTEGER | Timestamp | Singleton org-wide report config |
| 26 | `report_templates` | INTEGER | Timestamp, SoftDelete | Reusable report configurations |
| 27 | `queued_reports` | INTEGER | Timestamp | Report generation queue |
| 28 | `distribution_schedules` | INTEGER | Timestamp, SoftDelete | Automated report delivery |
| 29 | `construction_projects` | INTEGER | Timestamp | Phoenix MSA development pipeline |
| 30 | `construction_source_logs` | INTEGER | *(custom timestamps)* | Data import audit trail |
| 31 | `construction_permit_data` | INTEGER | Timestamp | Time-series permit data |
| 32 | `construction_employment_data` | INTEGER | Timestamp | BLS employment time-series |
| 33 | `construction_brokerage_metrics` | INTEGER | Timestamp | Quarterly brokerage metrics |
| 34 | `sales_data` | INTEGER | Timestamp | CoStar sales transactions |
| 35 | `monitored_files` | UUID | Timestamp | SharePoint file tracking |
| 36 | `file_change_logs` | UUID | Timestamp | File change audit trail |
| 37 | `reminder_dismissals` | INTEGER | Timestamp | Dismissed import reminders |

**Total: 37 tables**

---

## Mixins

### TimestampMixin (`backend/app/models/base.py`)

Applied to most tables. Adds:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `created_at` | TIMESTAMPTZ | NOT NULL | `datetime.now(UTC)` | Indexed |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `datetime.now(UTC)` | Auto-updates via `onupdate` |

### SoftDeleteMixin (`backend/app/models/base.py`)

Applied to: `users`, `properties`, `deals`, `transactions`, `documents`, `underwriting_models`, `report_templates`, `distribution_schedules`.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `is_deleted` | BOOLEAN | NOT NULL | `false` | Indexed |
| `deleted_at` | TIMESTAMPTZ | NULL | - | Set on soft delete |

### SourceTrackingMixin (`backend/app/models/underwriting/source_tracking.py`)

Applied to all underwriting child tables plus `underwriting_models`. Adds:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `source_file_name` | VARCHAR(500) | NULL | - | Source Excel file name |
| `source_file_path` | TEXT | NULL | - | Full SharePoint/file path |
| `source_file_modified_at` | TIMESTAMPTZ | NULL | - | Source file last modified |
| `extracted_at` | TIMESTAMPTZ | NULL | - | When data was extracted |
| `extraction_version` | VARCHAR(50) | NULL | - | Extraction script version |
| `extraction_status` | VARCHAR(20) | NULL | `'pending'` | pending/success/partial/error |
| `extraction_errors` | TEXT | NULL | - | Error details |

---

## Core Tables

### `users`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `email` | VARCHAR(255) | NOT NULL | - | Yes (unique) | |
| `hashed_password` | VARCHAR(255) | NOT NULL | - | No | |
| `full_name` | VARCHAR(255) | NOT NULL | - | No | |
| `role` | VARCHAR(50) | NOT NULL | `'viewer'` | No | admin/manager/analyst/viewer |
| `is_active` | BOOLEAN | NOT NULL | `true` | No | |
| `is_verified` | BOOLEAN | NOT NULL | `false` | No | |
| `avatar_url` | VARCHAR(500) | NULL | - | No | |
| `department` | VARCHAR(100) | NULL | - | No | |
| `phone` | VARCHAR(20) | NULL | - | No | |
| `last_login` | TIMESTAMPTZ | NULL | - | No | |
| `refresh_token` | TEXT | NULL | - | No | |
| `email_notifications` | BOOLEAN | NOT NULL | `true` | No | |
| `report_subscriptions` | TEXT | NULL | - | No | JSON string |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |

### `properties`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `property_type` | VARCHAR(50) | NOT NULL | - | Yes | multifamily/office/retail/industrial |
| `address` | VARCHAR(500) | NOT NULL | - | No | |
| `city` | VARCHAR(100) | NOT NULL | - | Yes | |
| `state` | VARCHAR(50) | NOT NULL | - | Yes | |
| `zip_code` | VARCHAR(20) | NOT NULL | - | No | |
| `county` | VARCHAR(100) | NULL | - | No | |
| `market` | VARCHAR(100) | NULL | - | Yes | |
| `submarket` | VARCHAR(100) | NULL | - | No | |
| `latitude` | NUMERIC(10,6) | NULL | - | No | |
| `longitude` | NUMERIC(10,6) | NULL | - | No | |
| `building_type` | VARCHAR(50) | NULL | - | No | |
| `year_built` | INTEGER | NULL | - | No | |
| `year_renovated` | INTEGER | NULL | - | No | |
| `total_units` | INTEGER | NULL | - | No | |
| `total_sf` | INTEGER | NULL | - | No | |
| `lot_size_acres` | NUMERIC(10,2) | NULL | - | No | |
| `stories` | INTEGER | NULL | - | No | |
| `parking_spaces` | INTEGER | NULL | - | No | |
| `purchase_price` | NUMERIC(15,2) | NULL | - | No | |
| `current_value` | NUMERIC(15,2) | NULL | - | No | |
| `acquisition_date` | DATE | NULL | - | No | |
| `occupancy_rate` | NUMERIC(5,2) | NULL | - | No | |
| `avg_rent_per_unit` | NUMERIC(10,2) | NULL | - | No | |
| `avg_rent_per_sf` | NUMERIC(8,2) | NULL | - | No | |
| `noi` | NUMERIC(15,2) | NULL | - | No | |
| `cap_rate` | NUMERIC(5,3) | NULL | - | No | |
| `financial_data` | JSON | NULL | - | No | Nested frontend fields |
| `description` | TEXT | NULL | - | No | |
| `amenities` | JSON | NULL | - | No | |
| `unit_mix` | JSON | NULL | - | No | |
| `images` | JSON | NULL | - | No | |
| `external_id` | VARCHAR(100) | NULL | - | Yes (unique) | |
| `data_source` | VARCHAR(50) | NULL | - | No | |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |

### `deals`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `version` | INTEGER | NOT NULL | `1` | No | **Optimistic locking** |
| `name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `deal_type` | VARCHAR(50) | NOT NULL | - | Yes | acquisition/disposition/development |
| `stage` | ENUM(DealStage) | NOT NULL | `'initial_review'` | Yes | values_callable lowercase |
| `stage_order` | INTEGER | NOT NULL | `0` | No | Kanban ordering within stage |
| `property_id` | INTEGER | NULL | - | Yes | FK -> properties.id |
| `assigned_user_id` | INTEGER | NULL | - | Yes | FK -> users.id |
| `asking_price` | NUMERIC(15,2) | NULL | - | No | |
| `offer_price` | NUMERIC(15,2) | NULL | - | No | |
| `final_price` | NUMERIC(15,2) | NULL | - | No | |
| `projected_irr` | NUMERIC(6,3) | NULL | - | No | |
| `projected_coc` | NUMERIC(6,3) | NULL | - | No | |
| `projected_equity_multiple` | NUMERIC(5,2) | NULL | - | No | |
| `hold_period_years` | INTEGER | NULL | - | No | |
| `initial_contact_date` | DATE | NULL | - | No | |
| `loi_submitted_date` | DATE | NULL | - | No | |
| `due_diligence_start` | DATE | NULL | - | No | |
| `due_diligence_end` | DATE | NULL | - | No | |
| `target_close_date` | DATE | NULL | - | No | |
| `actual_close_date` | DATE | NULL | - | No | |
| `source` | VARCHAR(100) | NULL | - | No | |
| `broker_name` | VARCHAR(255) | NULL | - | No | |
| `broker_company` | VARCHAR(255) | NULL | - | No | |
| `competition_level` | VARCHAR(50) | NULL | - | No | low/medium/high |
| `notes` | TEXT | NULL | - | No | |
| `investment_thesis` | TEXT | NULL | - | No | |
| `key_risks` | TEXT | NULL | - | No | |
| `documents` | JSON | NULL | - | No | |
| `activity_log` | JSON | NULL | - | No | |
| `tags` | JSON | NULL | - | No | |
| `custom_fields` | JSON | NULL | - | No | |
| `deal_score` | INTEGER | NULL | - | No | |
| `priority` | VARCHAR(20) | NOT NULL | `'medium'` | Yes | low/medium/high/urgent |
| `stage_updated_at` | TIMESTAMPTZ | NULL | - | No | |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |

**Composite Index:** `ix_deals_stage_stage_order` on (`stage`, `stage_order`) -- Kanban board ordering

### `transactions`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `property_id` | INTEGER | NULL | - | Yes | FK -> properties.id |
| `property_name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `type` | VARCHAR(50) | NOT NULL | - | Yes | acquisition/disposition/capital_improvement/refinance/distribution |
| `category` | VARCHAR(100) | NULL | - | Yes | |
| `amount` | NUMERIC(15,2) | NOT NULL | - | No | |
| `date` | DATE | NOT NULL | - | Yes | |
| `description` | TEXT | NULL | - | No | |
| `documents` | JSON | NULL | - | No | |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |

### `documents`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `type` | VARCHAR(50) | NOT NULL | - | Yes | lease/financial/legal/due_diligence/photo/other |
| `property_id` | VARCHAR(50) | NULL | - | Yes | **String type, not FK** |
| `property_name` | VARCHAR(255) | NULL | - | No | |
| `size` | INTEGER | NOT NULL | `0` | No | Bytes |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL | - | Yes | |
| `uploaded_by` | VARCHAR(255) | NULL | - | No | |
| `description` | TEXT | NULL | - | No | |
| `tags` | JSON | NULL | - | No | |
| `url` | VARCHAR(2048) | NULL | - | No | |
| `file_path` | VARCHAR(1024) | NULL | - | No | |
| `mime_type` | VARCHAR(255) | NULL | - | No | |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |

**Note:** `property_id` is VARCHAR(50), not an FK to `properties.id` (INTEGER). Known schema anomaly.

---

## Extraction Tables

### `extraction_runs`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | UUID | PK | uuid4 | Yes | |
| `started_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |
| `completed_at` | TIMESTAMPTZ | NULL | - | No | |
| `status` | VARCHAR(50) | NOT NULL | `'running'` | Yes | running/completed/failed/cancelled |
| `trigger_type` | VARCHAR(50) | NOT NULL | `'manual'` | No | manual/scheduled |
| `files_discovered` | INTEGER | NOT NULL | `0` | No | |
| `files_processed` | INTEGER | NOT NULL | `0` | No | |
| `files_failed` | INTEGER | NOT NULL | `0` | No | |
| `error_summary` | JSON | NULL | - | No | |
| `per_file_status` | JSON | NULL | - | No | Retry/resume support |
| `file_metadata` | JSON | NULL | - | No | Per-file statistics |
| + TimestampMixin | | | | | |

**Relationship:** One-to-many -> `extracted_values` (cascade: all, delete-orphan)

### `extracted_values`

EAV (Entity-Attribute-Value) pattern -- each extracted field becomes a row.

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | UUID | PK | uuid4 | Yes | |
| `extraction_run_id` | UUID | NOT NULL | - | Yes | FK -> extraction_runs.id (CASCADE) |
| `property_id` | INTEGER | NULL | - | Yes | FK -> properties.id (SET NULL) |
| `property_name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `field_name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `field_category` | VARCHAR(100) | NULL | - | No | |
| `sheet_name` | VARCHAR(100) | NULL | - | No | |
| `cell_address` | VARCHAR(20) | NULL | - | No | |
| `value_text` | TEXT | NULL | - | No | Universal text representation |
| `value_numeric` | NUMERIC(20,4) | NULL | - | No | Large financial numbers |
| `value_date` | DATE | NULL | - | No | |
| `is_error` | BOOLEAN | NOT NULL | `false` | No | |
| `error_category` | VARCHAR(50) | NULL | - | No | |
| `source_file` | VARCHAR(500) | NULL | - | No | |
| + TimestampMixin | | | | | |

**Unique Constraint:** `uq_extracted_value` on (`extraction_run_id`, `property_name`, `field_name`)
**Composite Index:** `idx_extracted_values_lookup` on (`property_name`, `field_name`)

---

## Underwriting Tables

All underwriting child tables share:
- FK `underwriting_model_id` -> `underwriting_models.id` (ON DELETE CASCADE), indexed
- TimestampMixin columns
- SourceTrackingMixin columns (7 columns for extraction lineage)

### `underwriting_models` (parent)

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `version` | INTEGER | NOT NULL | `1` | No | Scenario versioning |
| `scenario_name` | VARCHAR(100) | NULL | - | No | Base Case/Upside/Downside |
| `property_id` | INTEGER | NULL | - | Yes | FK -> properties.id |
| `deal_id` | INTEGER | NULL | - | Yes | FK -> deals.id |
| `created_by_user_id` | INTEGER | NULL | - | No | FK -> users.id |
| `status` | ENUM(UnderwritingStatus) | NOT NULL | `'draft'` | Yes | values_callable lowercase |
| `approved_by_user_id` | INTEGER | NULL | - | No | FK -> users.id |
| `approved_at` | TIMESTAMPTZ | NULL | - | No | |
| `description` | TEXT | NULL | - | No | |
| `notes` | TEXT | NULL | - | No | |
| + TimestampMixin | | | | | |
| + SoftDeleteMixin | | | | | |
| + SourceTrackingMixin | | | | | |

**Relationships (one-to-one, cascade all, delete-orphan):** general_assumptions, exit_assumptions, noi_assumptions, financing_assumptions, budget_assumptions, property_returns, equity_returns

**Relationships (one-to-many, cascade all, delete-orphan):** unit_mixes, rent_comps, sales_comps, annual_cashflows

### `uw_general_assumptions` (32 fields)

Key columns: `property_name`, `property_city`, `property_state`, `year_built`, `year_renovated`, `location_quality`, `building_quality`, `units`, `avg_square_feet` (NUMERIC(10,2)), `parking_spaces_covered`, `parking_spaces_uncovered`, `individually_metered`, `current_owner`, `last_sale_date`, `last_sale_price` (NUMERIC(15,2)), `property_street_address`, `property_zip_code`, `property_county`, `property_latitude` (NUMERIC(10,7)), `property_longitude` (NUMERIC(10,7)), `total_sf`, `stories`, `buildings`, `lot_size_acres` (NUMERIC(10,4)), `building_type`, `analysis_date`, `t12_end_date`, `acquisition_date`, `asset_class`, `submarket`, `msa`

### `uw_exit_assumptions` (3 fields)

`exit_period_months` (INTEGER), `exit_cap_rate` (NUMERIC(6,4)), `sales_transaction_costs` (NUMERIC(6,4))

### `uw_noi_assumptions` (65+ fields)

**Revenue:** `market_rent_per_unit`, `market_rent_per_sf`, `in_place_rent_per_unit`, `loss_to_lease_pct`, `rent_growth_year_1` through `_5`, vacancy rates (physical, economic, bad_debt, concessions, model, employee), other income categories (utility_reimbursement, parking, pet, late_fee, application_fee per unit), `other_income_growth_rate`.

**Expenses:** administrative, marketing, professional_fees, payroll categories (total, management, maintenance, taxes/benefits), utilities (total, electricity, gas, water_sewer, trash), R&M (repairs_maintenance, contract_services, make_ready, landscaping), insurance, real_estate_taxes, tax_reassessment_pct, management_fee_pct, asset_management_fee_pct, growth rates (expense, insurance, tax, utility). All per-unit.

**Capital:** `replacement_reserves_per_unit`, `capital_reserve_pct`.

**Metrics:** `total_revenue_per_unit`, `total_expenses_per_unit`, `noi_per_unit`, `expense_ratio`, `break_even_occupancy`, T-12 reference values (gpr, vacancy_loss, concessions, bad_debt, other_income, egi, total_expenses, noi), renovation premium assumptions (4 fields).

### `uw_financing_assumptions` (53 fields)

**Senior debt (19):** loan amount, LTV/LTC, interest rate + type + index + spread + floor + cap, term/amort/IO months, maturity date, origination/exit fees, closing costs, min DSCR + DSCR at close, lender name + type.
**Mezzanine (6):** amount, rate, term, origination fee, accrual rate, participation pct.
**Equity (11):** total equity required, LP/GP pct and amounts, preferred return + accrual type, catchup pct, 3 promote tiers (hurdle + GP split each).
**Fees (3):** acquisition, disposition, refinance fee pct.

### `uw_budget_assumptions` (32 fields)

**Purchase (4):** purchase_price, price_per_unit, price_per_sf, going_in_cap_rate.
**Closing costs (9):** title, survey, environmental, appraisal, legal, transfer_taxes, other, total, closing_costs_pct.
**Unit renovation (7):** interior, appliance, flooring, countertops, fixtures per unit; total per unit; total budget.
**Exterior/common (5):** exterior, common_area, amenity, landscaping, parking improvements.
**Building systems (4):** HVAC, roof, plumbing, electrical.
**Totals (3):** total_renovation_budget, contingency_pct, contingency_amount, total_project_cost, total_cost_per_unit, total_cost_per_sf.

### `uw_property_returns` (44 fields)

**Cap rates (5):** going_in, year_1, stabilized, exit, spread.
**NOI projections (8):** T-12, year_1 through year_5, stabilized, exit.
**Property value (7):** purchase_price, total_cost_basis, stabilized_value, exit_value, gross/net sale proceeds, value_creation.
**Unlevered returns (4):** IRR, equity multiple, CoC year_1, CoC avg.
**Yield (3):** year_1_yield_on_cost, stabilized_yield_on_cost, development_spread.
**Cash flow (6):** year_1 through year_5, total.
**Per unit (4):** NOI year_1, NOI stabilized, value purchase, value exit.

### `uw_equity_returns` (21 fields)

**Levered (4):** IRR, equity multiple, CoC year_1, CoC avg.
**LP (5):** IRR, equity multiple, total distributions, preferred return, profit share.
**GP (5):** IRR, equity multiple, total distributions, promote earned, fees earned.
**Waterfall (3):** total equity invested, total distributions, total profit.
**Promote (4):** tier achieved, tier 1/2/3 amounts.

### `uw_unit_mix` (normalized, per-unit-type rows)

`unit_type`, `unit_type_code`, `bedrooms`, `bathrooms` (NUMERIC(3,1)), `unit_count`, `unit_count_pct`, `avg_sf`, `total_sf`, `in_place_rent`, `in_place_rent_per_sf`, `market_rent`, `market_rent_per_sf`, `loss_to_lease`, `loss_to_lease_pct`, `proforma_rent`, `proforma_rent_per_sf`, `rent_premium_post_renovation`, `units_to_renovate`, `renovation_cost_per_unit`, `total_renovation_cost`, `renovation_scope`, `monthly_gpr`, `annual_gpr`.

### `uw_rent_comps` (normalized, per-comp rows)

`comp_number`, property ID (name, address, city, state, zip, distance_miles), physical (year_built, year_renovated, total_units, total_sf, avg_unit_sf, stories, building_type), quality (asset_class, condition, amenity_score), rent (avg_rent, per_sf, studio/1br/2br/3br rents, growth YoY, concessions, effective_rent), occupancy (occupancy_pct, vacancy_pct, leasing_velocity, avg_lease_term), ownership (owner, management), data (date, source, notes).

### `uw_sales_comps` (normalized, per-comp rows)

`comp_number`, property ID (name, address, city, state, zip, submarket, distance), physical (year_built, year_renovated, total_units, total_sf, avg_unit_sf, stories, building_type, lot_size_acres), quality (asset_class, condition_at_sale), transaction (sale_date, sale_price, price_per_unit, price_per_sf, transaction_type, sale_conditions), financials (cap_rate, cap_rate_type, noi_at_sale, noi_per_unit), rent (avg_rent_at_sale, per_sf, occupancy), parties (buyer/seller name + type, broker), financing (type, loan_amount, ltv), data (source, notes).

### `uw_annual_cashflows` (normalized, per-year rows)

`year_number`, `period_label`, period dates (start, end), `is_partial_year`.
**Revenue (15):** GPR, vacancy_loss, loss_to_lease, concessions, bad_debt, model/employee_unit_loss, net_rental_income, other income items (6), total_other_income, EGI.
**Expenses (15):** admin, marketing, professional_fees, payroll (total + management + maintenance + taxes), utilities (total + 4 subtypes), R&M (4), insurance, real_estate_taxes, management_fee, total_operating_expenses.
**NOI**, capital (replacement_reserves, capex, renovation_costs), debt service (senior total + interest + principal, mezz, total), cash flow (before/after debt), distributions (LP, GP, total), metrics (DSCR, CoC, occupancy, expense_ratio).

---

## Activity and Audit Tables

### `property_activities`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `property_id` | INTEGER | NOT NULL | - | Yes | FK -> properties.id |
| `user_id` | INTEGER | NOT NULL | - | Yes | FK -> users.id |
| `activity_type` | ENUM(ActivityType) | NOT NULL | - | Yes | values_callable lowercase |
| `description` | TEXT | NULL | - | No | |
| `field_changed` | VARCHAR(100) | NULL | - | No | |
| `old_value` | TEXT | NULL | - | No | |
| `new_value` | TEXT | NULL | - | No | |
| `comment_text` | TEXT | NULL | - | No | |
| `document_name` | VARCHAR(255) | NULL | - | No | |
| `document_url` | VARCHAR(500) | NULL | - | No | |
| `ip_address` | VARCHAR(45) | NULL | - | No | |
| `user_agent` | VARCHAR(500) | NULL | - | No | |
| + TimestampMixin | | | | | |

### `deal_activities`

Same structure as `property_activities` but with `deal_id` (INTEGER, NOT NULL, FK -> deals.id) instead of `property_id`.

### `user_watchlists`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `user_id` | INTEGER | NOT NULL | - | Yes | FK -> users.id |
| `deal_id` | INTEGER | NOT NULL | - | Yes | FK -> deals.id |
| `notes` | TEXT | NULL | - | No | |
| `alert_on_stage_change` | BOOLEAN | NOT NULL | `true` | No | |
| `alert_on_price_change` | BOOLEAN | NOT NULL | `true` | No | |
| `alert_on_document` | BOOLEAN | NOT NULL | `false` | No | |
| + TimestampMixin | | | | | |

**Unique Constraint:** `uq_user_deal_watchlist` on (`user_id`, `deal_id`)

### `activity_logs` (UUID-based deal audit trail)

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | UUID (PG_UUID) | PK | uuid4 | Yes | String(36) variant for SQLite |
| `deal_id` | INTEGER | NOT NULL | - | Yes | FK -> deals.id (CASCADE) |
| `user_id` | VARCHAR(255) | NULL | - | Yes | String for future auth flexibility |
| `action` | ENUM(ActivityAction) | NOT NULL | - | Yes | values_callable lowercase |
| `description` | TEXT | NOT NULL | - | No | |
| `metadata` | JSONB (PG) / JSON (SQLite) | NULL | - | No | Python attr: `meta`; DB column: `metadata` |
| `created_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | Yes | |

### `audit_logs_admin`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | Yes | |
| `timestamp` | TIMESTAMPTZ | NOT NULL | now(UTC) | Yes | |
| `user_id` | INTEGER | NOT NULL | - | Yes | **Not a FK** (intentional) |
| `user_email` | VARCHAR(255) | NOT NULL | - | No | |
| `action` | VARCHAR(100) | NOT NULL | - | Yes | |
| `resource_type` | VARCHAR(100) | NOT NULL | - | Yes | |
| `resource_id` | VARCHAR(255) | NULL | - | No | |
| `details` | TEXT | NULL | - | No | JSON-serialized context |
| `ip_address` | VARCHAR(45) | NULL | - | No | |
| `user_agent` | VARCHAR(500) | NULL | - | No | |
| `created_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |

---

## Reporting Tables

### `report_settings` (singleton)

| Column | Type | Nullable | Default (server_default) | Notes |
|--------|------|----------|--------------------------|-------|
| `id` | INTEGER | PK | auto | |
| `company_name` | VARCHAR(255) | NOT NULL | `'B&R Capital'` | |
| `company_logo` | VARCHAR(1024) | NULL | - | |
| `primary_color` | VARCHAR(20) | NOT NULL | `'#1e40af'` | |
| `secondary_color` | VARCHAR(20) | NOT NULL | `'#059669'` | |
| `default_font` | VARCHAR(100) | NOT NULL | `'Inter'` | |
| `default_page_size` | VARCHAR(10) | NOT NULL | `'letter'` | |
| `default_orientation` | VARCHAR(10) | NOT NULL | `'portrait'` | |
| `include_page_numbers` | BOOLEAN | NOT NULL | `true` | |
| `include_table_of_contents` | BOOLEAN | NOT NULL | `true` | |
| `include_timestamp` | BOOLEAN | NOT NULL | `true` | |
| `footer_text` | VARCHAR(500) | NOT NULL | `'Confidential - For Internal Use Only'` | |
| `header_text` | VARCHAR(500) | NOT NULL | `'B&R Capital Real Estate Analytics'` | |
| `watermark_text` | VARCHAR(255) | NULL | - | |
| + TimestampMixin | | | | |

### `report_templates`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | INTEGER | PK | auto | |
| `name` | VARCHAR(255) | NOT NULL | - | |
| `description` | TEXT | NULL | - | |
| `category` | ENUM(ReportCategory) | NOT NULL | `'custom'` | values_callable |
| `sections` | JSON | NOT NULL | `[]` | |
| `export_formats` | JSON | NOT NULL | `['pdf']` | |
| `is_default` | BOOLEAN | NOT NULL | `false` | |
| `created_by` | VARCHAR(255) | NOT NULL | `'System'` | |
| `config` | JSON | NULL | - | |
| + TimestampMixin | | | | |
| + SoftDeleteMixin | | | | |

### `queued_reports`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | INTEGER | PK | auto | |
| `name` | VARCHAR(255) | NOT NULL | - | |
| `template_id` | INTEGER | NOT NULL | - | FK -> report_templates.id |
| `status` | ENUM(ReportStatus) | NOT NULL | `'pending'` | values_callable |
| `progress` | INTEGER | NOT NULL | `0` | |
| `format` | ENUM(ReportFormat) | NOT NULL | `'pdf'` | values_callable |
| `requested_by` | VARCHAR(255) | NOT NULL | - | |
| `requested_at` | TIMESTAMPTZ | NOT NULL | - | |
| `completed_at` | TIMESTAMPTZ | NULL | - | |
| `file_size` | VARCHAR(50) | NULL | - | |
| `download_url` | VARCHAR(500) | NULL | - | |
| `error` | TEXT | NULL | - | |
| + TimestampMixin | | | | |

### `distribution_schedules`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | INTEGER | PK | auto | |
| `name` | VARCHAR(255) | NOT NULL | - | |
| `template_id` | INTEGER | NOT NULL | - | FK -> report_templates.id |
| `recipients` | JSON | NOT NULL | `[]` | |
| `frequency` | ENUM(ScheduleFrequency) | NOT NULL | - | values_callable |
| `day_of_week` | INTEGER | NULL | - | 0-6 for weekly |
| `day_of_month` | INTEGER | NULL | - | 1-31 for monthly |
| `time` | VARCHAR(5) | NOT NULL | - | HH:MM format |
| `format` | ENUM(ReportFormat) | NOT NULL | `'pdf'` | values_callable |
| `is_active` | BOOLEAN | NOT NULL | `true` | |
| `last_sent` | TIMESTAMPTZ | NULL | - | |
| `next_scheduled` | TIMESTAMPTZ | NOT NULL | - | |
| + TimestampMixin | | | | |
| + SoftDeleteMixin | | | | |

---

## Construction Pipeline Tables

### `construction_projects` (~90 columns)

Key groups:

- **Identity:** `id` (PK), `costar_property_id`, `property_type`, `project_name`, `project_address`
- **Geography:** `city`, `state` (default 'AZ'), `zip_code`, `county`, `latitude` (FLOAT), `longitude` (FLOAT), `market_name`, `submarket_name`, `submarket_cluster`
- **Status:** `pipeline_status` (VARCHAR(50), default 'proposed'), `constr_status_raw`, `building_status_raw`, `primary_classification` (VARCHAR(50), default 'CONV_MR'), `secondary_tags`
- **Building:** `number_of_units`, `building_sf` (FLOAT), `number_of_stories`, `total_buildings`, `star_rating`, `building_class`, `style`, `secondary_type`, `construction_material`, `is_condo` (BOOLEAN), `number_of_elevators`, `ceiling_height`, `sprinklers`
- **Unit Mix (pct):** `pct_studio` through `pct_4bed` (FLOAT)
- **Unit Mix (counts):** `num_studios` through `num_4bed` (INTEGER), `num_beds_total`, `avg_unit_sf`
- **Rent:** `rent_type`, `affordable_type`, `market_segment`, avg asking/effective per unit/sf, concessions, vacancy, pct_leased, pre_leasing
- **Timeline:** `construction_begin`, `year_built`, `month_built`, `year_renovated`, `month_renovated`, `estimated_delivery_date`
- **Developer/Owner:** developer_name, owner_name, owner_contact, architect_name, property_manager_name
- **Sale:** for_sale_price/status/per_unit/per_sf, cap_rate, last_sale_date/price, days_on_market
- **Land/Parking:** land_area_ac/sf, zoning, parking_spaces/per_unit/ratio
- **Flood:** fema_flood_zone (TEXT), flood_risk_area, in_sfha
- **Financing:** origination_amount/date, originator, interest_rate/type, loan_type, maturity_date
- **Tax:** tax_year, taxes_per_sf, taxes_total
- **Amenities/Misc:** amenities, features, transit, university, energy_star, leed_certified
- **Source:** source_type (default 'costar'), source_file, imported_at
- + TimestampMixin

**Unique Constraint:** `uq_construction_projects_costar_source` on (`costar_property_id`, `source_file`)

### `construction_source_logs`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | | |
| `source_name` | VARCHAR(100) | NOT NULL | - | Yes | |
| `fetch_type` | VARCHAR(50) | NOT NULL | - | No | |
| `fetched_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | Yes | |
| `records_fetched` | INTEGER | NOT NULL | `0` | No | |
| `records_inserted` | INTEGER | NOT NULL | `0` | No | |
| `records_updated` | INTEGER | NOT NULL | `0` | No | |
| `success` | BOOLEAN | NOT NULL | `true` | No | |
| `error_message` | TEXT | NULL | - | No | |
| `api_response_code` | INTEGER | NULL | - | No | |
| `data_period_start` | DATE | NULL | - | No | |
| `data_period_end` | DATE | NULL | - | No | |
| `created_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |

### `construction_permit_data`

`source` (VARCHAR(50)), `series_id` (VARCHAR(200)), `geography`, `period_date` (DATE), `period_type`, `value` (FLOAT), `unit`, `structure_type`, `raw_json` (TEXT), `source_log_id` (FK -> construction_source_logs.id) + TimestampMixin.

**Unique:** `uq_permit_data_source_series_period` on (`source`, `series_id`, `period_date`)
**Indexes:** `ix_construction_permit_source_series`, `ix_construction_permit_period`

### `construction_employment_data`

`series_id` (VARCHAR(200)), `series_title`, `period_date` (DATE), `value` (FLOAT), `period_type` (default 'monthly'), `source_log_id` (FK) + TimestampMixin.

**Unique:** `uq_employment_series_period` on (`series_id`, `period_date`)
**Index:** `ix_employment_series_date` on (`series_id`, `period_date`)

### `construction_brokerage_metrics`

`report_source` (VARCHAR(200)), `report_quarter` (VARCHAR(10)), `report_year`, `metric_name`, `metric_value` (FLOAT), `notes`, `entered_by`, `source_log_id` (FK) + TimestampMixin.

**Unique:** `uq_brokerage_source_quarter_metric` on (`report_source`, `report_quarter`, `metric_name`)

---

## Market Data Tables

### `sales_data` (~100 columns)

CoStar multifamily sales transaction records.

- **Import metadata:** `source_file`, `imported_at`, `market`
- **Core identifiers (10):** property_name, property_id, comp_id, address, city, state, zip, lat, lng, county
- **Geography (4):** submarket_cluster, submarket_name, parcel_number_1_min, parcel_number_2_max
- **Land/Building (8):** land_area_ac/sf, location_type, star_rating, market_column, submarket_code, building_class, affordable_type
- **Parties (12):** buyer/seller true company + contacts, acquisition/disposition fund names, listing/buyer broker companies + agent names
- **Building (13):** construction_begin, year_built, year_renovated, age, property_type, building_sf, materials, condition, construction_material, roof, ceiling, secondary_type, floors
- **Units/Parking (7):** number_of_units, parking_spaces, tenants, land sf gross/net, flood risk/zone
- **Transaction (13):** sale_date, sale_price, price_per_unit, price_per_sf variants, hold_period, document_number, down_payment, sale_type/condition/comment/status/category
- **Financial (10):** actual_cap_rate, units_per_acre, zoning, beds, gross_income, GRM, GIM, operating_expenses, total_expense, vacancy
- **Assessment (4):** assessed improved/land/value/year
- **Unit mix (5):** studios, 1-3BR, other bedrooms
- **Debt (9):** first/second trust deed details, title company
- **Notes (5):** amenities, sewer, transaction_notes, description, research_status
- + TimestampMixin

**Unique:** `uq_sales_data_comp_id_source` on (`comp_id`, `source_file`)
**Indexes:** `ix_sales_data_submarket`, `ix_sales_data_sale_date`, `ix_sales_data_market`

---

## File Monitoring Tables

### `monitored_files`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | UUID | PK | uuid4 | Yes | |
| `file_path` | VARCHAR(500) | NOT NULL | - | Yes (unique) | |
| `file_name` | VARCHAR(255) | NOT NULL | - | No | |
| `deal_name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `size_bytes` | BIGINT | NOT NULL | - | No | |
| `modified_date` | TIMESTAMPTZ | NOT NULL | - | No | |
| `content_hash` | VARCHAR(64) | NULL | - | No | SHA-256 |
| `first_seen` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |
| `last_checked` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |
| `last_extracted` | TIMESTAMPTZ | NULL | - | No | |
| `is_active` | BOOLEAN | NOT NULL | `true` | No | |
| `extraction_pending` | BOOLEAN | NOT NULL | `false` | No | |
| `extraction_run_id` | UUID | NULL | - | Yes | FK -> extraction_runs.id (SET NULL) |
| `deal_stage` | VARCHAR(50) | NULL | - | No | |
| + TimestampMixin | | | | | |

**Composite Indexes:** `idx_monitored_files_deal` on (`deal_name`, `is_active`); `idx_monitored_files_pending` on (`extraction_pending`, `is_active`)

### `file_change_logs`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | UUID | PK | uuid4 | Yes | |
| `file_path` | VARCHAR(500) | NOT NULL | - | Yes | |
| `file_name` | VARCHAR(255) | NOT NULL | - | No | |
| `deal_name` | VARCHAR(255) | NOT NULL | - | Yes | |
| `change_type` | VARCHAR(20) | NOT NULL | - | Yes | added/modified/deleted |
| `old_modified_date` | TIMESTAMPTZ | NULL | - | No | |
| `new_modified_date` | TIMESTAMPTZ | NULL | - | No | |
| `old_size_bytes` | BIGINT | NULL | - | No | |
| `new_size_bytes` | BIGINT | NULL | - | No | |
| `detected_at` | TIMESTAMPTZ | NOT NULL | now(UTC) | No | |
| `monitored_file_id` | UUID | NULL | - | Yes | FK -> monitored_files.id (SET NULL) |
| `extraction_triggered` | BOOLEAN | NOT NULL | `false` | No | |
| `extraction_run_id` | UUID | NULL | - | No | FK -> extraction_runs.id (SET NULL) |
| + TimestampMixin | | | | | |

**Index:** `idx_file_change_logs_detected` on (`detected_at`)

---

## Utility Tables

### `reminder_dismissals`

| Column | Type | Nullable | Default | Indexed | Notes |
|--------|------|----------|---------|---------|-------|
| `id` | INTEGER | PK | auto | | |
| `user_identifier` | VARCHAR(255) | NOT NULL | - | No | |
| `dismissed_month` | VARCHAR(7) | NOT NULL | - | Yes | YYYY-MM format |
| `dismissed_at` | TIMESTAMPTZ | NOT NULL | - | No | |
| + TimestampMixin | | | | | |

**Unique:** `uq_reminder_dismissal_user_month` on (`user_identifier`, `dismissed_month`)

---

## Foreign Key Relationships

| Source Table | Column | Target Table | Column | ON DELETE |
|-------------|--------|--------------|--------|----------|
| `deals` | `property_id` | `properties` | `id` | NO ACTION |
| `deals` | `assigned_user_id` | `users` | `id` | NO ACTION |
| `transactions` | `property_id` | `properties` | `id` | NO ACTION |
| `extracted_values` | `extraction_run_id` | `extraction_runs` | `id` | **CASCADE** |
| `extracted_values` | `property_id` | `properties` | `id` | **SET NULL** |
| `underwriting_models` | `property_id` | `properties` | `id` | NO ACTION |
| `underwriting_models` | `deal_id` | `deals` | `id` | NO ACTION |
| `underwriting_models` | `created_by_user_id` | `users` | `id` | NO ACTION |
| `underwriting_models` | `approved_by_user_id` | `users` | `id` | NO ACTION |
| `uw_general_assumptions` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_exit_assumptions` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_noi_assumptions` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_financing_assumptions` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_budget_assumptions` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_property_returns` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_equity_returns` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_unit_mix` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_rent_comps` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_sales_comps` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `uw_annual_cashflows` | `underwriting_model_id` | `underwriting_models` | `id` | **CASCADE** |
| `property_activities` | `property_id` | `properties` | `id` | NO ACTION |
| `property_activities` | `user_id` | `users` | `id` | NO ACTION |
| `deal_activities` | `deal_id` | `deals` | `id` | NO ACTION |
| `deal_activities` | `user_id` | `users` | `id` | NO ACTION |
| `user_watchlists` | `user_id` | `users` | `id` | NO ACTION |
| `user_watchlists` | `deal_id` | `deals` | `id` | NO ACTION |
| `activity_logs` | `deal_id` | `deals` | `id` | **CASCADE** |
| `queued_reports` | `template_id` | `report_templates` | `id` | NO ACTION |
| `distribution_schedules` | `template_id` | `report_templates` | `id` | NO ACTION |
| `construction_permit_data` | `source_log_id` | `construction_source_logs` | `id` | NO ACTION |
| `construction_employment_data` | `source_log_id` | `construction_source_logs` | `id` | NO ACTION |
| `construction_brokerage_metrics` | `source_log_id` | `construction_source_logs` | `id` | NO ACTION |
| `monitored_files` | `extraction_run_id` | `extraction_runs` | `id` | **SET NULL** |
| `file_change_logs` | `monitored_file_id` | `monitored_files` | `id` | **SET NULL** |
| `file_change_logs` | `extraction_run_id` | `extraction_runs` | `id` | **SET NULL** |

**Total: 35 foreign keys**

---

## Index Inventory

### Explicit Named Indexes

| Table | Index Name | Columns | Type |
|-------|-----------|---------|------|
| `deals` | `ix_deals_stage_stage_order` | `stage`, `stage_order` | Composite B-tree |
| `extracted_values` | `idx_extracted_values_lookup` | `property_name`, `field_name` | Composite B-tree |
| `monitored_files` | `idx_monitored_files_deal` | `deal_name`, `is_active` | Composite B-tree |
| `monitored_files` | `idx_monitored_files_pending` | `extraction_pending`, `is_active` | Composite B-tree |
| `file_change_logs` | `idx_file_change_logs_detected` | `detected_at` | B-tree |
| `construction_projects` | `ix_construction_projects_submarket` | `submarket_cluster` | B-tree |
| `construction_projects` | `ix_construction_projects_status` | `pipeline_status` | B-tree |
| `construction_projects` | `ix_construction_projects_classification` | `primary_classification` | B-tree |
| `construction_projects` | `ix_construction_projects_city` | `city` | B-tree |
| `construction_source_logs` | `ix_construction_source_logs_source` | `source_name` | B-tree |
| `construction_source_logs` | `ix_construction_source_logs_fetched` | `fetched_at` | B-tree |
| `construction_permit_data` | `ix_construction_permit_source_series` | `source`, `series_id` | Composite B-tree |
| `construction_permit_data` | `ix_construction_permit_period` | `period_date` | B-tree |
| `construction_employment_data` | `ix_employment_series_date` | `series_id`, `period_date` | Composite B-tree |
| `sales_data` | `ix_sales_data_submarket` | `submarket_name` | B-tree |
| `sales_data` | `ix_sales_data_sale_date` | `sale_date` | B-tree |
| `sales_data` | `ix_sales_data_market` | `market` | B-tree |
| `reminder_dismissals` | `ix_reminder_dismissals_month` | `dismissed_month` | B-tree |

### Column-Level `index=True` Indexes (auto-generated names)

| Table | Indexed Columns |
|-------|----------------|
| `users` | `id`, `email` (unique) |
| `properties` | `id`, `name`, `property_type`, `city`, `state`, `market`, `external_id` (unique) |
| `deals` | `id`, `name`, `deal_type`, `stage`, `property_id`, `assigned_user_id`, `priority` |
| `transactions` | `id`, `property_id`, `property_name`, `type`, `category`, `date` |
| `documents` | `id`, `name`, `type`, `property_id`, `uploaded_at` |
| `extraction_runs` | `id`, `status` |
| `extracted_values` | `id`, `extraction_run_id`, `property_id`, `property_name`, `field_name` |
| `underwriting_models` | `id`, `name`, `property_id`, `deal_id`, `status` |
| All UW child tables | `id`, `underwriting_model_id` |
| `property_activities` | `id`, `property_id`, `user_id`, `activity_type` |
| `deal_activities` | `id`, `deal_id`, `user_id`, `activity_type` |
| `user_watchlists` | `id`, `user_id`, `deal_id` |
| `activity_logs` | `id`, `deal_id`, `user_id`, `action`, `created_at` |
| `audit_logs_admin` | `id`, `timestamp`, `user_id`, `action`, `resource_type` |
| `monitored_files` | `id`, `file_path` (unique), `deal_name`, `extraction_run_id` |
| `file_change_logs` | `id`, `file_path`, `deal_name`, `change_type`, `monitored_file_id` |
| TimestampMixin | `created_at` (on all tables using mixin) |
| SoftDeleteMixin | `is_deleted` (on all tables using mixin) |

---

## CHECK Constraint Inventory

**Total: 41 CHECK constraints**

### `deals` (8 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_deals_asking_price_non_negative` | `asking_price >= 0` |
| `ck_deals_offer_price_non_negative` | `offer_price >= 0` |
| `ck_deals_final_price_non_negative` | `final_price >= 0` |
| `ck_deals_projected_irr_range` | `projected_irr >= -100 AND projected_irr <= 999` |
| `ck_deals_projected_coc_range` | `projected_coc >= -100` |
| `ck_deals_equity_multiple_non_negative` | `projected_equity_multiple >= 0` |
| `ck_deals_hold_period_positive` | `hold_period_years > 0` |
| `ck_deals_deal_score_range` | `deal_score >= 0 AND deal_score <= 100` |

### `properties` (12 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_properties_purchase_price_non_negative` | `purchase_price >= 0` |
| `ck_properties_current_value_non_negative` | `current_value >= 0` |
| `ck_properties_total_units_positive` | `total_units > 0` |
| `ck_properties_total_sf_positive` | `total_sf > 0` |
| `ck_properties_stories_positive` | `stories > 0` |
| `ck_properties_year_built_range` | `year_built >= 1800 AND year_built <= 2100` |
| `ck_properties_year_renovated_range` | `year_renovated >= 1800 AND year_renovated <= 2100` |
| `ck_properties_cap_rate_range` | `cap_rate >= 0 AND cap_rate <= 100` |
| `ck_properties_occupancy_rate_range` | `occupancy_rate >= 0 AND occupancy_rate <= 100` |
| `ck_properties_avg_rent_per_unit_non_negative` | `avg_rent_per_unit >= 0` |
| `ck_properties_avg_rent_per_sf_non_negative` | `avg_rent_per_sf >= 0` |
| `ck_properties_parking_spaces_non_negative` | `parking_spaces >= 0` |

### `transactions` (1 constraint)

| Constraint Name | Expression |
|----------------|------------|
| `ck_transactions_amount_non_negative` | `amount >= 0` |

### `uw_general_assumptions` (6 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_uw_general_assumptions_year_built_range` | `year_built >= 1800 AND year_built <= 2100` |
| `ck_uw_general_assumptions_year_renovated_range` | `year_renovated >= 1800 AND year_renovated <= 2100` |
| `ck_uw_general_assumptions_units_positive` | `units > 0` |
| `ck_uw_general_assumptions_last_sale_price_non_negative` | `last_sale_price >= 0` |
| `ck_uw_general_assumptions_total_sf_positive` | `total_sf > 0` |
| `ck_uw_general_assumptions_stories_positive` | `stories > 0` |

### `uw_unit_mix` (7 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_uw_unit_mix_unit_count_positive` | `unit_count > 0` |
| `ck_uw_unit_mix_bedrooms_non_negative` | `bedrooms >= 0` |
| `ck_uw_unit_mix_bathrooms_positive` | `bathrooms > 0` |
| `ck_uw_unit_mix_avg_sf_positive` | `avg_sf > 0` |
| `ck_uw_unit_mix_in_place_rent_non_negative` | `in_place_rent >= 0` |
| `ck_uw_unit_mix_market_rent_non_negative` | `market_rent >= 0` |
| `ck_uw_unit_mix_renovation_cost_non_negative` | `renovation_cost_per_unit >= 0` |

### `construction_projects` (2 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_construction_projects_number_of_units_positive` | `number_of_units > 0` |
| `ck_construction_projects_year_built_range` | `year_built >= 1800 AND year_built <= 2100` |

### `sales_data` (5 constraints)

| Constraint Name | Expression |
|----------------|------------|
| `ck_sales_data_sale_price_non_negative` | `sale_price >= 0` |
| `ck_sales_data_price_per_unit_non_negative` | `price_per_unit >= 0` |
| `ck_sales_data_number_of_units_positive` | `number_of_units > 0` |
| `ck_sales_data_year_built_range` | `year_built >= 1800 AND year_built <= 2100` |
| `ck_sales_data_actual_cap_rate_range` | `actual_cap_rate >= 0 AND actual_cap_rate <= 100` |

---

## Enum Types

All enums use `StrEnum` with `values_callable=lambda e: [m.value for m in e]` for lowercase storage.

| Enum | Values | Used In |
|------|--------|---------|
| `DealStage` | dead, initial_review, active_review, under_contract, closed, realized | `deals.stage` |
| `ActivityType` | view, edit, comment, status_change, document_upload | `property_activities`, `deal_activities` |
| `ActivityAction` | created, updated, stage_changed, document_added, document_removed, note_added, assigned, unassigned, price_changed, viewed | `activity_logs.action` |
| `UnderwritingStatus` | draft, in_progress, under_review, approved, rejected, archived | `underwriting_models.status` |
| `ReportCategory` | executive, financial, market, portfolio, custom | `report_templates.category` |
| `ReportFormat` | pdf, excel, pptx | `queued_reports.format`, `distribution_schedules.format` |
| `ReportStatus` | pending, generating, completed, failed | `queued_reports.status` |
| `ScheduleFrequency` | daily, weekly, monthly, quarterly | `distribution_schedules.frequency` |
| `PipelineStatus` | proposed, final_planning, permitted, under_construction, delivered | *(stored as VARCHAR, not PG ENUM)* |
| `ProjectClassification` | CONV_MR, CONV_CONDO, BTR, LIHTC, AGE_55, WORKFORCE, MIXED_USE, CONVERSION | *(stored as VARCHAR, not PG ENUM)* |
| `TransactionType` | acquisition, disposition, capital_improvement, refinance, distribution | *(stored as VARCHAR, not PG ENUM)* |
| `DocumentType` | lease, financial, legal, due_diligence, photo, other | *(stored as VARCHAR, not PG ENUM)* |

**Note:** The last 4 enums are Python StrEnums only. Their columns use plain VARCHAR, not PostgreSQL ENUM types.

---

## Model vs Live Schema Drift Notes

Since `pg_dump` was not accessible, these observations are from model analysis:

1. **`documents.property_id` is VARCHAR(50)** -- not an FK to `properties.id` (INTEGER). Known anomaly; may be intentional for storing external IDs.

2. **`audit_logs_admin.user_id` has no FK** -- INTEGER without ForeignKey to `users.id`. Intentional for tamper-evidence (audit log unaffected by user deletion).

3. **`construction_projects` uses plain VARCHAR for status/classification** -- `pipeline_status` and `primary_classification` have Python StrEnums but no PG ENUM or CHECK constraint enforcement at DB level.

4. **`transactions.type` and `documents.type`** -- plain VARCHAR despite Python StrEnum definitions.

5. **`activity_logs.meta` vs `metadata`** -- Python attribute is `meta`; DB column name is `metadata` (via `name="metadata"`). Avoids SQLAlchemy reserved attribute collision.

6. **Pending model changes not in Alembic** -- The Alembic HEAD is `7c415cc1b77a` (2026-02-12). These model features appear after that date and may have been applied via manual DDL or uncommitted migrations:
   - `audit_logs_admin` table
   - SoftDeleteMixin columns (`is_deleted`, `deleted_at`) on deals, transactions, properties, documents, users, underwriting_models, report_templates, distribution_schedules
   - `version` column (optimistic locking) on deals
   - `stage_order` column on deals
   - All 41 CHECK constraints
   - Composite index `ix_deals_stage_stage_order`

---

## Migration History

| # | Date | Revision | Description |
|---|------|----------|-------------|
| 1 | 2025-12-06 | `9fc6647c9407` | Initial: users, properties, deals, 12 UW tables, 3 activity tables |
| 2 | 2026-01-04 | `896670eb4597` | Add extraction_runs and extracted_values |
| 3 | 2026-01-06 | `a1b2c3d4e5f6` | Add monitored_files and file_change_logs |
| 4 | 2026-01-13 | `5a6a158ce7de` | Add transactions and documents |
| 5 | 2026-01-13 | `7b8c9d0e1f2a` | Add report_templates, queued_reports, distribution_schedules |
| 6 | 2026-02-02 | `8e6fdd43a452` | Add latitude, longitude, building_type, financial_data to properties |
| 7 | 2026-02-04 | `b2c3d4e5f6a7` | Align DealStage: 8-stage -> 6-stage model |
| 8 | 2026-02-07 | `c3d4e5f6a7b8` | Add report_settings table |
| 9 | 2026-02-07 | `351e79816af3` | Add sales_data table |
| 10 | 2026-02-11 | `9b81dcd19444` | Add per_file_status JSON to extraction_runs |
| 11 | 2026-02-11 | `b1e88c02306b` | Add file_metadata JSON to extraction_runs |
| 12 | 2026-02-11 | `2f2093cc37a2` | Add 5 construction pipeline tables |
| 13 | 2026-02-11 | `6f4865487bb2` | Widen fema_flood_zone VARCHAR(100) -> TEXT |
| 14 | 2026-02-12 | `d7d1ad81d3c0` | Add reminder_dismissals table |
| 15 | 2026-02-12 | `7c415cc1b77a` | Add activity_logs table (UUID-based) |

**Current Alembic HEAD:** `7c415cc1b77a`

---

*End of schema reference. Source: SQLAlchemy models in `backend/app/models/` and Alembic migrations in `backend/alembic/versions/`.*
