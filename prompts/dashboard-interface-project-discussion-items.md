# Dashboard Interface Project - Project Discussion Items

---

## Section 1: CoStar Market Data Integration

### 1.1 Current State Question

**Question**: How do the project scripts currently contemplate pulling market data?

**Proposed Approach**: Monthly manual download of CoStar files to a designated project folder that scripts can access.

---

### 1.2 File Inventory

#### Market-Level Files (6 files per MSA)

| File Type | Format | Example Filename |
|-----------|--------|------------------|
| Multifamily Market Report | PDF | `Multifamily Market Report (1.14.2026) – Phoenix, AZ USA.pdf` |
| Multifamily Capital Markets Report | PDF | `Multifamily Capital Markets Report (1.14.2026) – Phoenix, AZ USA.pdf` |
| About the Market Report | PDF | `About the Market Report (11.19.2025) – Phoenix, AZ USA.pdf` |
| Capital Markets Data Sheet | XLSX | `Capital Markets Data Sheet (1.14.2026) – Phoenix, AZ USA.xlsx` |
| Multifamily Market Overview | PPTX | `Multifamily Market Overview (11.17.2025) – Phoenix, AZ USA.pptx` |
| Market Data Export | XLSX | `Market Data Export (1.14.2026) – Phoenix, AZ USA.xlsx` |

#### Submarket-Level Files (4 files per MSA)

| File Type | Format | Example Filename |
|-----------|--------|------------------|
| Multifamily Submarket Report | PDF | `Multifamily Submarket Report (1.14.2026) – Phoenix, AZ USA (Tempe).pdf` |
| Multifamily Capital Markets Report | PDF | `Multifamily Capital Markets Report (1.14.2026) – Phoenix, AZ USA (Tempe).pdf` |
| Submarket Data Export | XLSX | `Submarket Data Export (1.14.2026) – Phoenix, AZ USA (All Submarkets).xlsx` |
| CoStar Submarket List | XLSX | `CoStar Submarket List (1.14.2026) – Phoenix, AZ USA (All Submarkets).xlsx` |

#### Sales Export Files (2 files per MSA)

| File Type | Format | Example Filename |
|-----------|--------|------------------|
| Multifamily Sales Export Data | XLSX | `Multifamily Sales Export Data (1.1.2000-12.31.2002) – Phoenix, AZ USA.xlsx` |
| Sales Export Criteria | MD | `Multifamily Sales Export Data – Sales Export Criteria.md` |

---

### 1.3 File Naming Convention Specification

**Pattern**: `[Report Type] ([DATE]) – [US MARKET], [US STATE] USA.ext`

**Submarket Pattern**: `[Report Type] ([DATE]) – [US MARKET], [US STATE] USA ([SUBMARKET]).ext`

**Sales Pattern**: `Multifamily Sales Export Data ([DATE_START]-[DATE_END]) – [US MARKET], [US STATE] USA.xlsx`

#### Date Location Reference (for automation)

| File Type | Date Location |
|-----------|---------------|
| PDF Reports | Footer on page 2+ |
| Capital Markets Data Sheet | Download date (manual) |
| Market Data Export | Download date (manual) |
| Multifamily Market Overview | First page, bottom left: "Date as of [DATE]" |
| Submarket Data Export | Download date (manual) |
| Sales Export | Derived from min/max of Column J "Sale Date" |

#### Market/State Location Reference (for automation)

| File Type | Location | Cell/Range |
|-----------|----------|------------|
| PDF Reports | Cover page | Below report title |
| Capital Markets Data Sheet | "All Property Types Annual" tab | C2:F2 (merged) |
| Market Data Export | "DataExport" tab | Column D "Geography Name" |
| Submarket Data Export | "DataExport" tab | Column D "Geography Name" |
| CoStar Submarket List | "GeographyList" tab | Column B "Market" |
| Sales Export | Tab with "Export" in name | Column P "Market" |

---

### 1.4 Sales Export Filter Criteria

Create `Multifamily Sales Export Data – Sales Export Criteria.md` with:

```markdown
# Sales Export Criteria

## Filter Settings
- **Sales Status**: Sold, Under Contract
- **Property Type**: Multifamily
- **Secondary Type**: Apartments
- **# of Units**: Min 25, No Max ("25+ Units")

## Data Layout
- **Field Layout**: All Field Export (1.13.2026)
```

---

### 1.5 Proposed Folder Structure

**Question**: Should each MSA have its own parent folder?

**Proposed Structure**:
```
market-data/
├── Market (Phoenix-AZ)/
│   ├── market-level/
│   │   ├── Multifamily Market Report (1.14.2026) – Phoenix, AZ USA.pdf
│   │   └── ...
│   ├── submarket-level/
│   │   ├── Multifamily Submarket Report (1.14.2026) – Phoenix, AZ USA (Tempe).pdf
│   │   └── ...
│   └── sales-export/
│       ├── Multifamily Sales Export Data (1.1.2000-12.31.2002) – Phoenix, AZ USA.xlsx
│       └── Multifamily Sales Export Data – Sales Export Criteria.md
├── Market (Tucson-AZ)/
│   └── ...
```

**Rationale**: Parent folder naming `Market ([US MARKET]-[US STATE])` enables the filename automation script to derive market/state from folder path when file metadata is ambiguous.

---

### 1.6 Filename Automation Script Requirements

**Purpose**: Validate and auto-correct filenames that don't match expected patterns.

**Workflow**:
1. Scan files in market folder
2. Compare filename against expected pattern for file type
3. If mismatch: extract components from file content (per location reference table above)
4. Rename file to match convention
5. Fallback: derive market/state from parent folder name

**Edge Cases to Handle**:
- PDFs without parseable text (scanned images)
- Excel files with non-standard tab names
- Files missing date metadata

---

### 1.7 Monthly Reminder System

**Requirement**: Popup notification on 15th of each month listing all reports to download.

**Reminder Content per MSA**:

**Market-Level (6 items)**:
- Multifamily Market Report
- Multifamily Capital Markets Report
- About the Market Report
- Capital Markets Data Sheet
- Multifamily Market Overview
- Market Data Export

**Submarket-Level (4 items)**:
- Multifamily Submarket Report
- Multifamily Capital Markets Report
- Submarket Data Export
- CoStar Submarket List

**Sales Export (1 item)**:
- Multifamily Sales Export Data

**Implementation Options**:
1. OS-level scheduled task with notification
2. Dashboard-integrated reminder system
3. Calendar integration (Outlook/Google)

---

### 1.8 Reference Documentation Request

**Question**: Should we create a reference document for market data files in the `docs/` folder?

**Recommendation**: Yes. Contents should include:
- File inventory table
- Naming conventions
- Date/market extraction locations
- Folder structure specification
- Automation script usage

---

## Section 2: Dashboard - Hosting & Deployment

### 2.1 Hosting Platform Selection

**Current State**: Local development server

**Goal**: Production deployment accessible to business partner

**Discussion Points**:
1. What platforms are recommended?
2. What are the implications for database, files, and other components?
3. Would Dockerization help with transition and scaling?

**Evaluation Criteria**:
- Cost (startup budget considerations)
- Ease of deployment
- PostgreSQL support
- File storage for market data
- Authentication/access control

---

### 2.2 Dockerization Assessment

**Questions**:
1. Would containerization smooth the local→production transition?
2. What scaling benefits would Docker provide?
3. Which components should be containerized?
   - Frontend
   - Backend API
   - PostgreSQL
   - File storage/processing workers

---

## Section 3: Dashboard - Mock Data Removal

### 3.1 Current Behavior

**Problem**: Dashboard falls back to mock data on errors, masking real issues.

### 3.2 Required Behavior

Replace mock data fallback with error display showing:
1. **Error details** - Specific error causing data retrieval failure
2. **Potential causes** - List of likely reasons
3. **Resolution steps** - Actionable troubleshooting guidance

**Applies to**:
- Frontend mock data fallback
- Database mock data (if stored in PostgreSQL)
- Any hardcoded fallback values in project files

---

## Section 4: Database Schema Verification

### 4.1 Schema Structure Question

**Expected Structure** (per `UW Model - Cell Reference Table` tab):

| Element | Source |
|---------|--------|
| Table Name | Column B "Cell Value Category" (e.g., "General Assumptions", "Exit Assumptions", "NOI Assumptions") |
| Table Columns | Column C "Cell Description" values for that category (e.g., "PROPERTY_NAME", "PROPERTY_CITY", "PROPERTY_STATE") |

**Verification Needed**: Does the current schema match this structure?

### 4.2 Mock Data Location

**Question**: Is mock data stored in PostgreSQL or hardcoded in application files?

**Action**: Identify and remove all mock data sources.

---

## Section 5: SharePoint Data Extraction

### 5.1 Extraction Completeness

**Question**: Is the extraction process pulling all 1,150+ data points from `Underwriting_Dashboard_Cell_References.xlsx`?

**Sub-questions**:
1. What are the common extraction failure patterns?
2. Which specific values frequently fail?
3. How does the script handle: blanks, zeros, N/A, Excel errors, null values?

---

### 5.2 Incremental Extraction Logic

**Requirements for subsequent extraction runs**:

| Scenario | Expected Behavior |
|----------|-------------------|
| File unchanged since last extraction | Skip (no re-extraction) |
| File modified since last extraction | Re-extract all 1,150+ data points; store with unique extraction identifier |
| File deleted from SharePoint | **Retain** database records (do NOT delete historical data) |

**Key**: Each extraction must be uniquely identifiable (timestamp, version ID, etc.)

---

### 5.3 Historical File Extraction

**Current Constraint**: Files must have modification date ≥ 7/15/2024

**Request**: Enable extraction from older UW Model files.

**Proposed Approach**:
1. Analyze pre-7/15/2024 files for structural compatibility
2. Group files by structure/layout similarity
3. Create variant `Underwriting_Dashboard_Cell_References.xlsx` for each group
4. Run extraction with appropriate reference file per group

**Output Needed**: Report showing which older files match current structure vs. require variant reference files.

---

### 5.4 Extraction Workflow Features (Confirm Implementation)

- [ ] Automatic default configuration
- [ ] Environment variable support
- [ ] Batch processing capabilities
- [ ] Error categorization and handling

---

### 5.5 Monitoring System Status

**If implemented**:
1. How does it work?
2. Check frequency for file updates/new files?
3. Does file change auto-trigger extraction?

**If not implemented**:
1. When will it be implemented?

**Expected Features**:
- Delta token management for efficient change detection
- File criteria filtering (date, name pattern, location)
- Automatic extraction queueing
- Database deduplication checking
- WebSocket server for real-time communication
- Health monitoring and recovery
- Graceful shutdown handling
- Dashboard integration callbacks

---

## Section 6: Third-Party Data Sources

### 6.1 Data Source Categorization

**Paid Subscriptions (Defer)**:
- CoStar - Covered in Section 1
- RealPage
- Trepp
- Yardi Matrix

**Free/API-Accessible (Implement)**:
- FRED (Federal Reserve Economic Data)
- Census Bureau
- Other sources per `multifamily_data_guide.docx`

---

### 6.2 API Credentials

| Source | API Key | Reference |
|--------|---------|-----------|
| FRED | `d043d26a9a4139438bb2a8d565bc01f7` | Page 2 (top), 15, 17 of multifamily_data_guide |
| Census Bureau | `0145eb3254e9885fa86407a72b6b0fb381e846e8` | Page 2 (bottom), 16 of multifamily_data_guide |

---

### 6.3 Data Categories (per multifamily_data_guide)

| Category | Guide Page |
|----------|------------|
| Economic Data | 3 |
| Financial Data | 4 |
| Housing Data | 5 |
| Demographic Data | 6 |
| Construction Data | 7 |
| Zoning & Entitlement Data | 8 |
| Other Market Data | 9 |
| Labor Market Data | 10 |
| Cost Factors Data | 11 |
| Leading Indicators | 12 |
| Risk/Stress Indicators | 13 |
| Phoenix MSA Specific Series | 14 |

---

## Section 7: Machine Learning Features

### 7.1 General ML Integration

- Anomaly detection for unusual extraction patterns
- Predictive queueing based on upload patterns
- Automatic error classification and resolution

### 7.2 Predictive & Advanced Analytics

- Market Timing Intelligence
- Cash Flow Forecasting
- Investment Grading
- Economic Sensitivity

### 7.3 Historical Pattern Recognition

- Multiple variable pattern identification

### 7.4 Risk Scoring & Evaluation

| Feature | Description |
|---------|-------------|
| Project Risk Assessment | Monte Carlo + other frameworks |
| Portfolio Risk Aggregation | Roll-up metrics across properties |
| Automated Risk Alerts | Notifications for high-risk assessments |
| Risk Report Templates | Standardized assessment reports |
| ML Models | Predictive scoring from historical data |
| Stress Testing | Economic scenario modeling |
| Predictive Analytics | Early warning systems |
| IRR Forecast | Monte Carlo simulation |

---

## Section 8: Mobile Functionality

### 8.1 Timing Question

**Question**: At what project stage should mobile development begin?

### 8.2 Feature Ideas

- Offline capability
- Push notifications
- Native app experience

---

## Section 9: Other Improvements & Enhancements

### 9.1 Performance & Infrastructure

- [ ] Advanced Caching - Redis-based acceleration
- [ ] WSL2 Networking Compatibility
- [ ] Comprehensive Error Handling with NaN management
- [ ] Enhanced Data Export Options
- [ ] Historical Tracking - Version control for all properties

### 9.2 Document Intelligence

- [ ] Multi-format Support - PDF, Word, Excel, images via OCR
- [ ] Financial Extraction - Automated financial metric extraction
- [ ] Automated Document Analysis
- [ ] Risk Factor Extraction

### 9.3 Automated Reporting

- [ ] Scheduled Email Reports
- [ ] PDF Generation
- [ ] Export Automation

### 9.4 Performance Validation Tests

| Test | Target |
|------|--------|
| Dashboard load time | < 2s |
| Database query performance | < 0.5s |
| Excel extraction speed | TBD |

### 9.5 Testing Coverage

- [ ] End-to-end integration tests (SharePoint → Database → Dashboard)
- [ ] Error handling tests (Excel processing, database failures, authentication)
- [ ] CI/CD pipeline setup

---

## Section 10: Reference Documentation Locations

| Topic | File Path |
|-------|-----------|
| Dashboard | `PROJECT_COMPLETION_SUMMARY.md` |
| Database | `PROJECT_COMPLETION_SUMMARY.md` |
| SharePoint Extraction | `AUTO_EXTRACTION_SYSTEM_GUIDE.md`, `PROJECT_SUMMARY.md`, `PROJECT_COMPLETION_SUMMARY.md` |
| Third Party Data | `PROJECT_SUMMARY.md`, `docs/multifamily_data_guide.docx` |
| Machine Learning | `AUTO_EXTRACTION_SYSTEM_GUIDE.md`, `PHASE5_COMPLETION_SUMMARY.md`, `docs/PHASE_6.4_COMPLETE_SUMMARY.md`, `dash_app/services/analytics_service.py` |
| Mobile | `PROJECT_COMPLETION_SUMMARY.md` |
| Architecture | `worktrees/option-a-accept-noncritical/PROJECT_ARCHITECTURE_ANALYSIS.md` |

---

## Appendix: Action Items Summary

### Immediate (Decision Required)

1. **Section 1.5** - Confirm folder structure proposal
2. **Section 2.1** - Select hosting platform
3. **Section 4.1** - Verify database schema matches spec

### Investigation Needed

4. **Section 3.2** - Locate all mock data sources
5. **Section 5.1** - Audit extraction completeness (1,150+ fields)
6. **Section 5.3** - Analyze pre-7/15/2024 file structures
7. **Section 5.5** - Determine monitoring system status

### Implementation

8. **Section 1.6** - Build filename automation script
9. **Section 1.7** - Implement monthly reminder system
10. **Section 3.2** - Replace mock fallback with error display
11. **Section 6** - Integrate FRED and Census APIs

### Documentation

12. **Section 1.8** - Create market data reference doc in `docs/`
