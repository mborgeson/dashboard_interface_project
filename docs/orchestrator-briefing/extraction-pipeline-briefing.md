# Orchestrator Briefing: Excel Extraction Pipeline Optimization

**Date:** 2026-01-07
**Priority:** HIGH
**Project:** Dashboard Interface - B&R Capital UW Model Extraction
**Status:** Pipeline functional but performance-blocked

---

## Executive Summary

The SharePoint-to-Dashboard data extraction pipeline is **functionally complete** but faces a critical **performance bottleneck** that makes production use impractical. The system successfully:
- Discovers 30+ UW model files from SharePoint (~255 MB)
- Downloads and extracts ~1,179 cell mappings per file
- Stores 10,521+ extracted values in PostgreSQL

**THE PROBLEM:** Each `.xlsb` file takes **~111 seconds** to process due to an O(n²) cell lookup algorithm in the pyxlsb library handling. While an O(1) caching optimization was added, it may not be correctly utilized in all code paths.

---

## Problem Statement

### Current Performance
| Metric | Current | Target |
|--------|---------|--------|
| Time per file | ~111 seconds | <10 seconds |
| Files processed | 15+ (session ended) | 30+ |
| Success rate | 100% | 100% |
| Values per file | ~700 extracted | ~1,179 |

### Root Cause Analysis

The `pyxlsb` library for reading `.xlsb` (binary Excel) files does NOT support random cell access. To read cell D6:
1. Must open the sheet
2. Iterate through ALL rows until row 6
3. Iterate through ALL columns until column D
4. Return value

**Complexity:** O(rows × columns) per cell lookup × 1,179 mappings = O(n²) per file

### Attempted Fix (Partially Implemented)

A sheet caching mechanism was added to `extractor.py:325-352`:

```python
def _build_xlsb_sheet_cache(self, workbook, sheet_name: str) -> dict[tuple[int, int], Any]:
    """
    Build a cell lookup dictionary for an XLSB sheet.

    PERFORMANCE OPTIMIZATION: This converts O(n) sheet iteration into a
    one-time O(n) operation, enabling O(1) lookups for all subsequent
    cell accesses.
    """
    cell_cache: dict[tuple[int, int], Any] = {}

    with workbook.get_sheet(sheet_name) as sheet:
        for row in sheet.rows():
            for cell in row:
                cell_cache[(cell.r, cell.c)] = cell.v

    return cell_cache
```

**Issue:** The cache is stored on `workbook._sheet_cache` but:
1. May not persist correctly across the extraction loop
2. May be rebuilt for each mapping instead of once per sheet
3. The workbook context manager may clear state

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTRACTION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐             │
│  │ SharePoint  │───▶│  Discovery   │───▶│  FileFilter     │             │
│  │ Graph API   │    │  30 files    │    │  Pattern/Date   │             │
│  └─────────────┘    └──────────────┘    └─────────────────┘             │
│         │                                       │                        │
│         ▼                                       ▼                        │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐             │
│  │  Download   │───▶│  Cell        │───▶│  Extract        │◀── BOTTLENECK
│  │  to /tmp    │    │  Mappings    │    │  1,179 fields   │             │
│  └─────────────┘    │  (reference) │    └─────────────────┘             │
│                     └──────────────┘            │                        │
│                                                 ▼                        │
│                     ┌──────────────┐    ┌─────────────────┐             │
│                     │  PostgreSQL  │◀───│  CRUD Bulk      │             │
│                     │  extracted_  │    │  Insert         │             │
│                     │  values      │    └─────────────────┘             │
│                     └──────────────┘                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### File Formats
| Format | Library | Random Access | Notes |
|--------|---------|---------------|-------|
| `.xlsb` | pyxlsb | NO - streaming only | Main bottleneck |
| `.xlsx` | openpyxl | YES | Works fine |
| `.xlsm` | openpyxl | YES | Works fine |

### Cell Mapping Reference File
- **Path:** `/home/mattb/projects/dashboard_interface_project/Underwriting_Dashboard_Cell_References.xlsx`
- **Size:** 6 MB
- **Mappings:** ~1,179 fields across multiple sheets
- **Sheet Name:** "UW Model - Cell Reference Table"

### Database Schema
```sql
-- extraction_runs table
id UUID PRIMARY KEY
status VARCHAR(50)  -- running, completed, failed, cancelled
files_discovered INTEGER
files_processed INTEGER
files_failed INTEGER
started_at TIMESTAMP
completed_at TIMESTAMP

-- extracted_values table
id UUID PRIMARY KEY
extraction_run_id UUID REFERENCES extraction_runs(id)
property_name VARCHAR(255)
field_name VARCHAR(255)
field_category VARCHAR(100)
sheet_name VARCHAR(100)
cell_address VARCHAR(20)
value_text TEXT
value_numeric NUMERIC
value_date TIMESTAMP
is_error BOOLEAN
```

---

## Codebase Reference

### Core Extraction Files

| File | LOC | Purpose |
|------|-----|---------|
| `backend/app/extraction/extractor.py` | 590 | Main extraction logic, BOTTLENECK HERE |
| `backend/app/extraction/cell_mapping.py` | 294 | Parses reference Excel file |
| `backend/app/extraction/error_handler.py` | 463 | Error handling, NaN conversion |
| `backend/app/extraction/sharepoint.py` | 644 | SharePoint Graph API client |
| `backend/app/extraction/file_filter.py` | 294 | Configurable filtering rules |
| `backend/app/api/v1/endpoints/extraction.py` | 1154 | REST API endpoints |
| `backend/app/crud/extraction.py` | 291 | Database CRUD operations |
| `backend/app/db/session.py` | 132 | Sync/Async session management |

### Key Methods to Analyze

1. **`ExcelDataExtractor.extract_from_file()`** - Lines 119-279
   - Entry point for extraction
   - Loops through 1,179 mappings
   - Calls `_extract_cell_value()` for each

2. **`ExcelDataExtractor._extract_from_xlsb()`** - Lines 354-410
   - Should use cache but may not be optimal
   - Check if cache persists across loop iterations

3. **`ExcelDataExtractor._build_xlsb_sheet_cache()`** - Lines 325-352
   - Cache building logic
   - O(n) one-time cost per sheet

4. **`run_extraction_task()`** in extraction.py API - Lines 111-271
   - Background task orchestration
   - Downloads files to temp directory

---

## Potential Solutions (For Agent Analysis)

### Option 1: Fix Existing Cache Implementation
- Verify `workbook._sheet_cache` persists correctly
- Ensure cache is built ONCE per sheet, not per mapping
- Add logging to verify cache hit rate

### Option 2: Pre-process All Sheets
- Before mapping loop, iterate ALL sheets and cache ALL cells
- Store in memory: `{sheet_name: {(row, col): value}}`
- Then iterate mappings with O(1) lookups

### Option 3: Group Mappings by Sheet
- Sort/group 1,179 mappings by `sheet_name`
- Process all mappings for one sheet before moving to next
- Open sheet once, extract all relevant cells, close

### Option 4: Alternative Libraries
- `xlrd` - Only supports `.xls`, not `.xlsb`
- `pandas` with `engine='pyxlsb'` - Same underlying issue
- `python-calamine` - Rust-based, claims better performance
- `xlwings` with Excel COM - Requires Windows/Excel installed

### Option 5: File Format Conversion
- Convert `.xlsb` to `.xlsx` on SharePoint or during download
- Use openpyxl which has random access
- Trade-off: Conversion time vs extraction time

### Option 6: Parallel Processing
- Current: Sequential file processing with ThreadPoolExecutor
- Enhance: True parallel cell extraction within a file
- Use multiprocessing for CPU-bound pyxlsb iteration

---

## Agent Team Assignment

### Phase 1: Analysis (perf-analyzer, code-analyzer)
**Goal:** Definitively identify where time is spent

Tasks:
1. Add timing instrumentation to `extract_from_file()`
2. Measure: cache build time, cache lookup time, per-mapping time
3. Verify cache is being used (log cache hits/misses)
4. Profile with cProfile or line_profiler
5. Determine if bottleneck is:
   - Cache not being used
   - Cache being rebuilt unnecessarily
   - I/O bound (file reading)
   - CPU bound (cell iteration)

### Phase 2: Solution Design (system-architect, backend-dev)
**Goal:** Design optimal fix based on analysis

Tasks:
1. Review Phase 1 findings
2. Select best solution approach
3. Design implementation plan
4. Consider backwards compatibility
5. Plan for testing/validation

### Phase 3: Implementation (coder, backend-dev)
**Goal:** Implement the fix

Tasks:
1. Implement chosen solution
2. Add comprehensive logging
3. Maintain existing API contracts
4. Ensure error handling preserved
5. Update type hints

### Phase 4: Testing & Validation (tester, production-validator)
**Goal:** Verify fix works correctly

Tasks:
1. Run existing tests: `pytest tests/test_extraction/`
2. Test with real `.xlsb` files from fixtures
3. Measure performance improvement
4. Validate data accuracy (compare before/after)
5. Stress test with full 30-file batch

### Phase 5: Documentation (reviewer)
**Goal:** Document changes

Tasks:
1. Update code comments
2. Update checkpoint document
3. Record performance metrics
4. Document any configuration changes

---

## Test Fixtures

Location: `backend/tests/fixtures/uw_models/*.xlsb`

Test commands:
```bash
cd /home/mattb/projects/dashboard_interface_project/backend
source venv/bin/activate

# Run extraction tests (includes performance measurement)
pytest tests/test_extraction/test_extractor.py -v -s

# Run quick manual test
python tests/test_extraction/test_extractor.py

# Run with profiling
python -m cProfile -s cumtime tests/test_extraction/test_extractor.py
```

---

## Environment Setup

```bash
# Navigate to project
cd /home/mattb/projects/dashboard_interface_project/backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
pip install pyxlsb openpyxl pandas structlog

# Set environment (avoid stale shell vars)
unset SHAREPOINT_SITE_URL
export PYTHONPATH=/home/mattb/projects/dashboard_interface_project/backend

# Verify setup
python -c "from app.extraction import ExcelDataExtractor; print('OK')"
```

---

## Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Per-file extraction time | ~111s | <15s | Timer in logs |
| Total 30-file batch | ~55 min | <10 min | End-to-end test |
| Memory usage | Unknown | <2GB | Monitor during batch |
| Accuracy | 100% | 100% | Compare extracted values |
| API response time | N/A | <30s start | Curl timing |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Optimization breaks extraction | HIGH | Comprehensive testing, compare outputs |
| Memory issues with caching | MEDIUM | Monitor memory, add limits if needed |
| pyxlsb library limitations | MEDIUM | Fallback to alternative approach |
| Breaking API changes | LOW | Maintain existing contracts |

---

## Communication Protocol

Agents should:
1. Log findings to memory with key: `extraction-optimization-{phase}`
2. Report blockers immediately
3. Update todo list with progress
4. Create checkpoint on phase completion

---

## Appendix: Key Code Snippets

### Current Extraction Loop (extractor.py:218-252)
```python
for i, (field_name, mapping) in enumerate(self.mappings.items()):
    try:
        value = self._extract_cell_value(
            workbook,
            mapping.sheet_name,
            mapping.cell_address,
            field_name,
            is_xlsb,
        )
        extracted_data[field_name] = value
        # ... success/failure tracking
    except Exception as e:
        # ... error handling

    # Progress callback every 100 fields
    if progress_callback and (i + 1) % 100 == 0:
        progress_callback(i + 1, total)
```

### Cache Building (extractor.py:387-400)
```python
# Get or build the sheet cache for O(1) cell lookups
if not hasattr(workbook, "_sheet_cache"):
    workbook._sheet_cache = {}

if sheet_name not in workbook._sheet_cache:
    workbook._sheet_cache[sheet_name] = self._build_xlsb_sheet_cache(
        workbook, sheet_name
    )

cell_cache = workbook._sheet_cache[sheet_name]

# O(1) lookup instead of O(cells) iteration
cell_value = cell_cache.get((target_row, target_col))
```

---

## Handoff Checklist

- [x] Problem clearly defined
- [x] All relevant files documented
- [x] Current state captured in checkpoint
- [x] Test fixtures available
- [x] Environment setup documented
- [x] Success criteria defined
- [x] Agent assignments specified
- [x] Risk assessment completed

---

*Briefing prepared: 2026-01-07*
*Ready for orchestrator assignment*
