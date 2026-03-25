# Discovery Document 03: Database Schema

**Project:** B&R Capital Dashboard Interface
**Date:** 2026-03-25
**Scope:** SQLAlchemy models, Alembic migrations, schema patterns, and data integrity constraints

---

## 1. Model Registry

Models are registered in two locations to serve different purposes:

| Registration Point | File | Purpose |
|---|---|---|
| Alembic (migrations) | `backend/app/db/base.py` | Auto-detection for `alembic revision --autogenerate` |
| Application imports | `backend/app/models/__init__.py` | Runtime model availability via `from app.models import ...` |

There are **17 model files** in `backend/app/models/`.

> **Note:** Both registration points must stay in sync. A model present in `__init__.py` but absent from `base.py` will be importable at runtime but invisible to Alembic, causing migration drift.

---

## 2. Base Mixins

Defined in `backend/app/models/base.py`:

### TimestampMixin

| Column | Type | Behavior |
|---|---|---|
| `created_at` | `DateTime` | Set to `datetime.now(UTC)` on insert |
| `updated_at` | `DateTime` | Set to `datetime.now(UTC)` on insert and update |

### SoftDeleteMixin

| Column | Type | Behavior |
|---|---|---|
| `deleted_at` | `DateTime` (nullable) | `NULL` = active; non-null = soft-deleted |

---

## 3. Core Models

### 3.1 User (`backend/app/models/user.py`)

**Table:** `users`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK | Auto-increment |
| `email` | String | Unique, not null | Login identifier |
| `hashed_password` | String | Not null | bcrypt hash |
| `full_name` | String | | Display name |
| `role` | String | | Used by `require_analyst`, `require_manager` guards |
| `is_active` | Boolean | | Account enable/disable flag |

- JWT auth integration: tokens issued at `POST /api/v1/auth/login`, validated by middleware in `backend/app/core/security.py`.

---

### 3.2 Property (`backend/app/models/property.py`)

**Table:** `properties`
**Mixins:** `TimestampMixin`, `SoftDeleteMixin`

#### Identity & Location

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `name` | String | Property name |
| `property_type` | String | e.g., multifamily |
| `address` | String | Street address |
| `city` | String | |
| `state` | String | |
| `zip_code` | String | |
| `county` | String | |
| `market` | String | MSA-level |
| `submarket` | String | CoStar submarket cluster |
| `latitude` | Numeric | |
| `longitude` | Numeric | |

#### Financial

| Column | Type | Notes |
|---|---|---|
| `purchase_price` | Numeric | Acquisition cost |
| `current_value` | Numeric | Current appraised/estimated value |
| `cap_rate` | Numeric | NOI / Purchase Price |
| `occupancy_rate` | Numeric | Physical or economic occupancy |
| `avg_rent_per_unit` | Numeric | Average monthly rent per unit |
| `avg_rent_per_sf` | Numeric | Average rent per square foot |

#### Physical

| Column | Type | Notes |
|---|---|---|
| `total_units` | Integer | Unit count |
| `total_sf` | Integer | Total square footage |
| `stories` | Integer | Building height |
| `year_built` | Integer | Original construction year |
| `year_renovated` | Integer | Most recent renovation |
| `parking_spaces` | Integer | |

#### CHECK Constraints

All CHECK constraints were added via migration `c5d6e7f8a9b0` (VARCHAR/enum CHECK constraints):

| Column | Constraint | Rationale |
|---|---|---|
| `purchase_price` | >= 0 | No negative prices |
| `current_value` | >= 0 | No negative valuations |
| `total_units` | > 0 | Must have at least one unit |
| `total_sf` | > 0 | Must have positive square footage |
| `stories` | > 0 | At least one story |
| `year_built` | 1800 -- 2100 | Reasonable construction date range |
| `year_renovated` | 1800 -- 2100 | Reasonable renovation date range |
| `cap_rate` | 0 -- 100 | Percentage range |
| `occupancy_rate` | 0 -- 100 | Percentage range |
| `avg_rent_per_unit` | >= 0 | No negative rent |
| `avg_rent_per_sf` | >= 0 | No negative rent |
| `parking_spaces` | >= 0 | Non-negative count |

---

### 3.3 Deal (`backend/app/models/deal.py`)

**Table:** `deals`

#### Enum: `DealStage` (StrEnum)

```
dead | initial_review | active_review | under_contract | closed | realized
```

Stored as lowercase strings via `values_callable`.

#### Core Fields

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK | |
| `version` | Integer | Not null, default 1 | Optimistic locking -- reject stale updates |
| `name` | String | Not null | Deal name |
| `deal_type` | String | | Classification |
| `stage` | Enum(`DealStage`) | | Current pipeline stage |
| `stage_order` | Integer | | Sort order within stage (kanban ordering) |

#### Foreign Keys

| Column | References | Notes |
|---|---|---|
| `property_id` | `properties.id` | The underlying asset |
| `assigned_user_id` | `users.id` | Deal lead / analyst |

#### Financial

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `asking_price` | Numeric | >= 0 | Seller's listed price |
| `offer_price` | Numeric | >= 0 | B&R's offer |
| `final_price` | Numeric | >= 0 | Executed purchase price |
| `projected_irr` | Numeric | -100 to 999 | LP Internal Rate of Return |
| `projected_coc` | Numeric | >= -100 | Cash-on-Cash return |
| `projected_equity_multiple` | Numeric | >= 0 | LP MOIC |
| `hold_period_years` | Numeric | > 0 | Target hold period |
| `deal_score` | Numeric | 0 -- 100 | Composite ranking score |

#### Timeline

| Column | Type |
|---|---|
| `initial_contact_date` | Date |
| `loi_submitted_date` | Date |
| `due_diligence_start` | Date |
| `due_diligence_end` | Date |
| `target_close_date` | Date |
| `actual_close_date` | Date |

#### JSON Columns

| Column | Type | Purpose |
|---|---|---|
| `documents` | JSON | Attached document references |
| `activity_log` | JSON | Inline activity history |
| `tags` | JSON | Flexible tagging |
| `custom_fields` | JSON | User-defined metadata |

#### Indexes

| Index | Columns | Purpose |
|---|---|---|
| `ix_deals_stage_stage_order` | `(stage, stage_order)` | Composite -- kanban board queries |

---

### 3.4 Document (`backend/app/models/document.py`)

**Table:** `documents`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | PK |
| `document_type` | Enum(`DocumentType`) | Classification enum |
| `property_id` | Integer FK | References `properties.id` |

---

## 4. Extraction Models (`backend/app/models/extraction.py`)

### 4.1 ExtractionRun

**Table:** `extraction_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `started_at` | DateTime | Run start timestamp |
| `completed_at` | DateTime | Run completion timestamp |
| `status` | String | e.g., running, completed, failed |
| `trigger_type` | String | manual, scheduled, file_change |
| `files_discovered` | Integer | Files found during scan |
| `files_processed` | Integer | Files successfully processed |
| `files_failed` | Integer | Files that errored |
| `error_summary` | JSON | Aggregated error information |
| `per_file_status` | JSON | Per-file processing details |
| `file_metadata` | JSON | Additional file-level metadata |

**Relationships:**
- One-to-many with `ExtractedValue` (cascade delete -- deleting a run removes all its values)

**Computed Properties:**
- `duration_seconds`: `completed_at - started_at`
- `success_rate`: `files_processed / files_discovered`

---

### 4.2 ExtractedValue (EAV Pattern)

**Table:** `extracted_values`

The Entity-Attribute-Value pattern is used here to avoid creating a table with 1,179+ columns (one per extractable field). Instead, each row represents a single extracted data point.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `extraction_run_id` | UUID FK | References `extraction_runs.id` (CASCADE) |
| `property_id` | Integer FK | References `properties.id` (SET NULL) |
| `property_name` | String | Denormalized -- survives property deletion |
| `field_name` | String | The metric name (e.g., `GOING_IN_CAP_RATE`) |
| `field_category` | String | Grouping category |
| `sheet_name` | String | Source Excel sheet |
| `cell_address` | String | Source cell reference (e.g., `D14`) |
| `value_text` | Text | String representation of value |
| `value_numeric` | Numeric(20,4) | Parsed numeric value (4 decimal places) |
| `value_date` | Date | Parsed date value |
| `is_error` | Boolean | Whether extraction encountered an error |
| `error_category` | String(50) | Error classification |
| `source_file` | String(500) | Full path to source Excel file |

**Constraints:**

| Constraint | Columns | Purpose |
|---|---|---|
| UniqueConstraint | `(extraction_run_id, property_name, field_name)` | One value per field per property per run |
| Index `idx_extracted_values_lookup` | `(property_name, field_name)` | Fast lookups for the Proforma Returns UI |

**Design Rationale:** The triple-value-column approach (`value_text`, `value_numeric`, `value_date`) allows type-appropriate storage and querying while the EAV structure keeps the schema stable as new extraction fields are added.

---

## 5. File Monitor Models (`backend/app/models/file_monitor.py`)

### MonitoredFile

Tracks the state of files in the monitored directory (SharePoint/OneDrive sync folder).

| Column | Type | Notes |
|---|---|---|
| `path` | String | Full file path |
| `name` | String | File name |
| `modified_date` | DateTime | Last modification timestamp |
| `size` | Integer | File size in bytes |
| `is_active` | Boolean | Whether file is still being tracked |

### FileChangeLog

Audit trail of detected file system changes.

---

## 6. Activity & Audit Models

### 6.1 Activity Models (`backend/app/models/activity.py`)

| Model | Purpose |
|---|---|
| `DealActivity` | Activity records tied to deals |
| `PropertyActivity` | Activity records tied to properties |
| `UserWatchlist` | User subscriptions to entity changes |

Uses `ActivityType` enum for classification.

### 6.2 ActivityLog (`backend/app/models/activity_log.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `action` | Enum(`ActivityAction`) | Create, update, delete, etc. |

UUID-based primary key for distributed-safe ID generation.

### 6.3 AuditLog (`backend/app/models/audit_log.py`)

System-level audit trail for compliance and debugging.

---

## 7. Underwriting Models (`backend/app/models/underwriting.py`)

Eleven models representing the full underwriting data structure:

| Model | Purpose |
|---|---|
| `UnderwritingModel` | Root model tying assumptions to a deal/property |
| `GeneralAssumptions` | Hold period, growth rates, market assumptions |
| `ExitAssumptions` | Exit cap rate, disposition costs, terminal value |
| `NOIAssumptions` | Revenue growth, expense ratios, vacancy |
| `FinancingAssumptions` | Loan terms, LTV, interest rate, amortization |
| `BudgetAssumptions` | Renovation/CapEx budget breakdown |
| `PropertyReturns` | Unlevered property-level returns |
| `EquityReturns` | Levered LP/GP return splits (IRR, MOIC) |
| `UnitMix` | Unit type breakdown (1BR, 2BR, etc.) with rents |
| `RentComp` | Comparable property rent data |
| `SalesComp` | Comparable sales transaction data |
| `AnnualCashflow` | Year-by-year projected cash flows |

---

## 8. Construction Models (`backend/app/models/construction.py`)

| Model | Purpose |
|---|---|
| `ConstructionProject` | Active construction projects in the market |
| `ConstructionSourceLog` | Data source tracking for construction data |
| `ConstructionPermitData` | Building permit filings |
| `ConstructionEmploymentData` | Construction employment metrics |
| `ConstructionBrokerageMetrics` | Brokerage-reported construction activity |

**Enums:**
- `PipelineStatus`: Project lifecycle stages
- `ProjectClassification`: Project type categorization

---

## 9. Report & Settings Models

| Model | File | Purpose |
|---|---|---|
| `ReportSettings` | `report_settings.py` | User-configurable report parameters |
| `ReportTemplate` | `report_template.py` | Saved report templates |
| `QueuedReport` | `report_template.py` | Background report generation queue |
| `DistributionSchedule` | `report_template.py` | Automated report distribution |

---

## 10. Other Models

| Model | File | Purpose |
|---|---|---|
| `SalesData` | `sales_data.py` | Market sales transaction records |
| `Transaction` | `transaction.py` | Financial transactions |
| `ReminderDismissal` | `reminder_dismissal.py` | Tracks dismissed UI reminders per user |

---

## 11. Alembic Migrations

**Migration directory:** `backend/alembic/versions/`
**Total migrations:** 20 files
**Current head:** `152c800e6789` (fix deal stages)

### Key Migration History

| Migration | Description | Impact |
|---|---|---|
| Initial | Schema creation | All core tables |
| Float to Numeric | Financial precision conversion | Prevents floating-point rounding in cap rates, prices, returns |
| Documents FK fix | Added `property_id` FK to documents | Fixed orphaned document records |
| Model drift catchup | Sync schema with model definitions | Resolved accumulated autogenerate drift |
| VARCHAR/enum CHECKs | Added CHECK constraints (`c5d6e7f8a9b0`) | Data integrity for properties, deals |
| Deal stage fixes | Stage enum corrections (`152c800e6789`) | Current head |

> **Rule:** Never edit existing migration files in `backend/alembic/versions/`. Only create new migrations.

---

## 12. Key Schema Patterns

### SQLAlchemy 2.0 Style

All models use the modern declarative syntax:

```python
class Property(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
```

### Async Sessions

All database access uses SQLAlchemy async sessions (`AsyncSession`). No synchronous database calls exist in the application code.

### Enum Storage

`StrEnum` with `values_callable` ensures enums are stored as lowercase strings rather than integer ordinals:

```python
class DealStage(StrEnum):
    dead = "dead"
    initial_review = "initial_review"
    # ...
```

### Primary Key Strategy

| Entity Type | PK Type | Examples |
|---|---|---|
| Core business entities | Integer (auto-increment) | User, Property, Deal, Document |
| Extraction & activity models | UUID | ExtractionRun, ExtractedValue, ActivityLog |

UUID keys on extraction and activity models support distributed-safe insertion (batch extraction runs, concurrent activity logging) without sequence contention.

### EAV Pattern (Extracted Values)

The `extracted_values` table uses Entity-Attribute-Value to avoid a wide table with 1,179+ columns. Each extracted data point is a row with `property_name` + `field_name` as the logical key. Trade-offs:

- **Pro:** Schema-stable as new extraction fields are added (no migration needed).
- **Pro:** Flexible querying across heterogeneous field types.
- **Con:** Queries for "all fields of a property" require pivoting or multiple rows.
- **Con:** No column-level type enforcement (relies on application-layer validation).

### JSON Columns

Used for flexible, schema-less metadata where relational normalization would be premature:

| Table | JSON Columns | Rationale |
|---|---|---|
| `deals` | `documents`, `activity_log`, `tags`, `custom_fields` | User-defined metadata, variable structure |
| `extraction_runs` | `error_summary`, `per_file_status`, `file_metadata` | Diagnostic data, variable per run |

### Optimistic Locking

The `deals.version` column implements optimistic concurrency control. Updates must include the current version number; the backend rejects stale writes where the version has been incremented by another request.

---

## 13. Entity Relationship Summary

```
users
  |-- 1:N --> deals (assigned_user_id)
  |-- 1:N --> user_watchlist

properties
  |-- 1:N --> deals (property_id)
  |-- 1:N --> documents (property_id)
  |-- 1:N --> extracted_values (property_id, SET NULL)
  |-- 1:N --> property_activity

deals
  |-- 1:N --> deal_activity

extraction_runs
  |-- 1:N --> extracted_values (CASCADE delete)

underwriting_model
  |-- 1:1 --> general_assumptions
  |-- 1:1 --> exit_assumptions
  |-- 1:1 --> noi_assumptions
  |-- 1:1 --> financing_assumptions
  |-- 1:1 --> budget_assumptions
  |-- 1:1 --> property_returns
  |-- 1:1 --> equity_returns
  |-- 1:N --> unit_mix
  |-- 1:N --> rent_comp
  |-- 1:N --> sales_comp
  |-- 1:N --> annual_cashflow
```

---

## 14. Testing Implications

- **SQLite in-memory** is used for backend tests (`StaticPool`).
- SQLite does not support `server_default` -- timestamps must be set explicitly in test fixtures using `datetime.now(UTC)`.
- `begin_nested()` is unreliable with `StaticPool` -- avoid savepoints in tests.
- CHECK constraints are enforced by SQLite, so test data must respect the bounds listed in Section 3.2 and 3.3.
