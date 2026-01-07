# Quick Start: Extraction Pipeline Optimization

## TL;DR

**Problem:** Excel extraction takes 111s per file instead of <15s
**Root Cause:** O(n²) cell lookup in pyxlsb (no random access)
**Fix Location:** `backend/app/extraction/extractor.py`
**Cache exists but may not work correctly**

---

## Fastest Path to Fix

### Step 1: Verify the Cache Issue (5 min)

Add this diagnostic to `extractor.py` line 393:

```python
if sheet_name not in workbook._sheet_cache:
    print(f"CACHE MISS: Building cache for {sheet_name}")  # ADD THIS
    workbook._sheet_cache[sheet_name] = self._build_xlsb_sheet_cache(
        workbook, sheet_name
    )
else:
    print(f"CACHE HIT: Using existing cache for {sheet_name}")  # ADD THIS
```

Run test:
```bash
cd /home/mattb/projects/dashboard_interface_project/backend
python tests/test_extraction/test_extractor.py
```

**Expected:** Should see "CACHE HIT" for same sheets (1,179 mappings spread across ~10 sheets)
**If you see:** Repeated "CACHE MISS" for same sheet = BUG FOUND

---

### Step 2: Fix Options

#### Option A: Group Mappings by Sheet First (RECOMMENDED)

Modify `extract_from_file()` to:
1. Group 1,179 mappings by `sheet_name`
2. For each sheet: build cache once, extract all cells, close
3. Eliminates repeated cache rebuilding

```python
# Before extraction loop, group mappings
from collections import defaultdict
mappings_by_sheet = defaultdict(list)
for field_name, mapping in self.mappings.items():
    mappings_by_sheet[mapping.sheet_name].append((field_name, mapping))

# Process sheet by sheet
for sheet_name, sheet_mappings in mappings_by_sheet.items():
    if is_xlsb:
        cache = self._build_xlsb_sheet_cache(workbook, sheet_name)
        for field_name, mapping in sheet_mappings:
            # Use cache directly
            value = cache.get((row, col))
```

#### Option B: Pre-build All Caches

Before the mapping loop, build caches for ALL sheets:
```python
if is_xlsb:
    # Pre-build all sheet caches
    workbook._sheet_cache = {}
    for sheet_name in workbook.sheets:
        workbook._sheet_cache[sheet_name] = self._build_xlsb_sheet_cache(workbook, sheet_name)
```

---

### Step 3: Validate Fix

```bash
# Run test and compare times
cd /home/mattb/projects/dashboard_interface_project/backend
time python tests/test_extraction/test_extractor.py

# Before fix: Duration ~111s per file
# After fix: Duration should be <15s per file
```

---

## File Locations Quick Reference

| What | Where |
|------|-------|
| Main extractor | `backend/app/extraction/extractor.py` |
| Cache building | Lines 325-352 |
| Extraction loop | Lines 218-252 |
| XLSB extraction | Lines 354-410 |
| Test files | `backend/tests/fixtures/uw_models/*.xlsb` |
| Test runner | `backend/tests/test_extraction/test_extractor.py` |
| Reference mappings | `Underwriting_Dashboard_Cell_References.xlsx` (project root) |

---

## Spawn Command for Orchestrator

```
/sparc:orchestrator

Task: Optimize Excel extraction pipeline performance

Briefing: /docs/orchestrator-briefing/extraction-pipeline-briefing.md

Phases:
1. perf-analyzer: Add instrumentation, identify exact bottleneck
2. system-architect: Design optimal solution
3. coder: Implement fix
4. tester: Validate performance improvement
5. reviewer: Document changes

Success: Per-file extraction <15s (currently 111s)
```

---

## SPARC Mode Alternative

```
/sparc tdd "Optimize pyxlsb cell extraction from 111s to <15s per file"
```

This will:
1. Write failing performance test
2. Implement fix
3. Verify test passes
4. Refactor if needed

---

## Claude-Flow Swarm Alternative

```bash
npx claude-flow@alpha sparc run optimizer "Fix O(n²) cell lookup in backend/app/extraction/extractor.py - target <15s per file extraction"
```

---

## Manual Agent Spawn

```javascript
// Parallel analysis agents
Task("perf-analyzer", "Profile extraction in backend/app/extraction/extractor.py. Add timing to _extract_from_xlsb and _build_xlsb_sheet_cache. Run tests/test_extraction/test_extractor.py and report where time is spent.", "perf-analyzer")

Task("code-analyzer", "Analyze cache implementation in backend/app/extraction/extractor.py lines 325-410. Verify workbook._sheet_cache persists correctly across the 1,179 mapping iterations.", "code-analyzer")
```

---

## Expected Timeline

| Phase | Agent | Duration |
|-------|-------|----------|
| Analysis | perf-analyzer | 10-15 min |
| Design | architect | 5 min |
| Implementation | coder | 15-20 min |
| Testing | tester | 10 min |
| Documentation | reviewer | 5 min |

**Total: ~45-55 minutes**

---

## Verification Checklist

After fix is applied:

- [ ] `pytest tests/test_extraction/test_extractor.py -v` passes
- [ ] Single file extraction <15 seconds
- [ ] Extracted values match expected count (~700+ per file)
- [ ] No regression in data accuracy
- [ ] Memory usage reasonable (<2GB for batch)
- [ ] API endpoints still work: `POST /extraction/start`
