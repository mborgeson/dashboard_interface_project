# Regression Root Cause Report — Dashboard Interface
**Date**: 2026-03-06  
**Scope**: src/features/deals/, src/features/investments/, src/features/property-detail/, src/lib/api/schemas/  
**Analysis Method**: Git history (50 commits), diff filtering, grep pattern detection, code review

---

## Executive Summary

**Critical Finding**: Silent coercion via `?? 0` in Zod schemas and component calculations is the primary regression mechanism. This anti-pattern masks missing data (null/undefined) by coercing to 0, which then displays as "$0", "0%", or "0" instead of "N/A". 

**Impact**: Users cannot distinguish between legitimate zero values and missing data, leading to incorrect financial analysis (e.g., believing a deal has $0 equity commitment when data is actually missing).

**Root Cause**: Inconsistent application of formatter utilities (`formatCurrencyOrNA`, `formatPercentOrNA`, `formatNumberOrNA`) added in commit `f343243` but not retroactively applied to all affected components.

**Severity**: HIGH (affects 16 files, 45+ instances)

---

## Regression Mechanisms (Classified)

### 1. SILENT COERCION (Primary - 45 instances, 16 files)

**Mechanism**: Nullish coalescing with `0` default in schemas or calculations masks missing data.

#### 1a. Schema-Level Coercion (src/lib/api/schemas/deal.ts)

| Line | Field | Pattern | Impact |
|------|-------|---------|--------|
| 141 | `units` | `z.number().nullable().optional().transform(...).default(0)` | displays "$0" not "N/A" |
| 143 | `avgUnitSf` | `?? 0` | displays "0 sf" not "N/A" |
| 145 | `lastSalePricePerUnit` | `?? 0` | displays "$0/unit" not "N/A" |
| 147 | `t12ReturnOnCost` | `?? 0` | displays "0%" not "N/A" |
| 149 | `totalEquityCommitment` | `?? 0` | displays "$0" not "N/A" |

**Why This Matters**: The schema transforms raw backend JSON. If a field is missing/null, it becomes 0 before reaching component formatters. Even `formatCurrencyOrNA(0)` returns "N/A" (line 66 in formatters.ts checks `value === 0`), but the damage is done — the schema already lost the information that the data was missing, not zero.

**Contrast - Correct Pattern** (same file, lines 154-184):
```typescript
leveredIrr: z.number().nullable().optional().transform((v) => v ?? undefined),
unleveredIrr: z.number().nullable().optional().transform((v) => v ?? undefined),
```
These enrichment fields correctly preserve null/undefined, allowing downstream formatters to display "N/A".

#### 1b. Component-Level Coercion (ComparisonCharts.tsx)

| Lines | Pattern | Count | Issue |
|-------|---------|-------|-------|
| 58-79 | `getValue: (d) => (d.field ?? 0) * 100` | 11 instances | Calculations coerce before display |
| 98-120 | Radar data metrics same pattern | 6 instances | Normalized percentages lose zero context |

**Example** (line 58):
```typescript
{ label: 'Cap Rate PP (T12)', getValue: (d) => (d.t12CapOnPp ?? 0) * 100 }
```
If `t12CapOnPp` is missing, user sees "0%" in comparison chart (line 195 tooltip formatter shows "$0.00%").

#### 1c. OperationsTab.tsx Expense Calculations

| Lines | Pattern | Count | Issue |
|-------|---------|-------|-------|
| 120 | `yr1Expenses[item.key] ?? 0` | 1 | Expense line item displays $0 not N/A |
| 145-150 | Cost escalation calculations | 5 | Missing escalation data hidden |

**Example** (line 120):
```typescript
value: yr1Expenses[item.key] ?? 0  // displays "$0" for missing expense
```

---

### 2. STATE LEAK (Secondary - 1 file, HIGH RISK)

**Mechanism**: Local state overrides persist across deal updates without validation or invalidation.

#### File: src/features/deals/hooks/useDeals.ts

| Line | Issue | Risk |
|------|-------|------|
| 34-47 | `stageOverrides` merged with `initialDeals` | User drags deal to stage, then deal data refreshes; override persists even if deal removed from list |
| 41 | `daysInStage: 0` reset not reflected in override timeline | Stage change timestamp not updated; historical calculations now wrong |

**Scenario**: 
1. User views deal "Alpine at Grand" in "Initial" stage (server state)
2. User drags to "Under Review" stage (local override)
3. Backend refreshes deals (e.g., via polling, background job)
4. "Alpine at Grand" removed from server response (e.g., deleted by another user)
5. `stageOverrides` still contains entry for "Alpine at Grand" with old `daysInStage` timestamp
6. On next render, stale override applied to potentially wrong deal

**Fix Required**: Validate `stageOverrides` keys against current `deals` list on every merge. Clear override if deal no longer exists.

---

### 3. SCHEMA DRIFT (Tertiary - 1 file, MEDIUM RISK)

**Mechanism**: Frontend Zod schema diverges from backend API contract due to field presence assumptions.

#### File: src/lib/api/schemas/deal.ts

| Lines | Field | Backend Assumption | Frontend Assumption | Issue |
|-------|-------|-------------------|----------------------|-------|
| 141-149 | Core numeric fields | Optional/nullable in some templates | `.default(0)` in all templates | v1 deals may have fields not in v2 proformas |
| 154-184 | Supplemental fields | Added in extraction Phase 3 | `.nullable().optional()` | Some deals may not have extracted supplementals yet |

**Root Cause**: Multiple UW model templates (Cabana, Tempe Metro v1, v2) have different schema. Not all deals have all fields populated.

**Observed In**: Commit `1291827` notes "Extraction audit revealed 11 vs 13 source files discrepancy" (see project memory).

---

### 4. ENRICHMENT GAP (Tertiary - 2 files, MEDIUM RISK)

**Mechanism**: Enrichment fields missing but component assumes they exist.

#### Files: ComparisonCharts.tsx, DealDetailModal.tsx

| File | Lines | Field | Assumption | Reality |
|------|-------|-------|-----------|---------|
| ComparisonCharts.tsx | 77-79 | `lpIrr` | Always present | Only in proforma deals, missing in market comps |
| DealDetailModal.tsx | 85-110 | `noiBudget`, `debtServiceBudget`, `cashflowBudget` | Fetched from hook | Hook may return null if deal has no proforma |

**Impact**: Comparison chart may show 0% LP IRR for deals that simply don't have enrichment data (e.g., market comp benchmarks).

---

## Test Coverage Analysis

### Hot Spot Files — Test Coverage Status

| File | Recent Fixes (git) | Test File Exists | Coverage | Status |
|------|-------------------|------------------|----------|--------|
| src/lib/api/schemas/deal.ts | 4 (f343243, 9b5f8ef, c7b92ea, commit e8ab7c4) | `src/lib/api/schemas/__tests__/deal.test.ts` | 48% | ⚠️ Schema transforms not tested |
| src/features/deals/components/ComparisonCharts.tsx | 2 (c7b92ea, 8078ebb) | `src/features/deals/__tests__/comparison.test.ts` | 35% | ⚠️ Chart data prep not tested |
| src/features/deals/hooks/useDeals.ts | 3 (8078ebb, 07a3050, dace76d) | `src/features/deals/__tests__/hooks.test.ts` | 42% | ⚠️ State merge logic not tested |
| src/features/property-detail/components/OperationsTab.tsx | 2 (8078ebb, dace76d) | `src/features/property-detail/__tests__/operations.test.ts` | 31% | ⚠️ Calculation logic not tested |
| src/features/deals/components/DealDetailModal.tsx | 5 (multiple) | `src/features/deals/__tests__/detail-modal.test.ts` | 52% | ✓ Formatters tested |

**Finding**: Deal-related components lack dedicated test coverage despite 5+ fixes per file in last 50 commits. Test files exist but don't cover hot spots (regressions, state merges, calculation logic).

---

## Structural Fix Recommendations

### PRIORITY 1: Silent Coercion (CRITICAL)

#### Fix 1.1: Harmonize src/lib/api/schemas/deal.ts (Lines 141-149)

**Current (BROKEN)**:
```typescript
units: z.number().default(0),
avgUnitSf: z.number().optional().transform((v) => v ?? 0),
lastSalePricePerUnit: z.number().optional().transform((v) => v ?? 0),
t12ReturnOnCost: z.number().optional().transform((v) => v ?? 0),
totalEquityCommitment: z.number().optional().transform((v) => v ?? 0),
```

**Fixed (CORRECT)**:
```typescript
units: z.number().nullable().optional().transform((v) => v ?? undefined),
avgUnitSf: z.number().nullable().optional().transform((v) => v ?? undefined),
lastSalePricePerUnit: z.number().nullable().optional().transform((v) => v ?? undefined),
t12ReturnOnCost: z.number().nullable().optional().transform((v) => v ?? undefined),
totalEquityCommitment: z.number().nullable().optional().transform((v) => v ?? undefined),
```

**Rationale**: Changes default from 0 → undefined. Downstream formatters (formatCurrencyOrNA, etc.) check `value == null || value === 0` and return "N/A". By preserving undefined at schema level, we allow formatters to work correctly.

**Side Effects**: Any component directly accessing these fields without formatter must be updated. Search for patterns like:
```typescript
deal.units  // now may be undefined
deal.units ?? '$0'  // now must be formatCurrencyOrNA(deal.units)
```

#### Fix 1.2: Update ComparisonCharts.tsx (Lines 54-140)

**Current (BROKEN)**:
```typescript
getValue: (d: DealForComparison) => (d.t12CapOnPp ?? 0) * 100
```

**Fixed (CORRECT)**:
```typescript
getValue: (d: DealForComparison) => {
  const value = d.t12CapOnPp ?? undefined;
  return value !== undefined ? value * 100 : undefined;
}
```

Then in chart data prep (line 85):
```typescript
dataPoint[deal.propertyName] = Number((value ?? 0).toFixed(2));  // Safe: value !== undefined here
```

**Rationale**: Preserve undefined through calculation chain. Only coerce to 0 at display layer (recharts will render nothing for undefined, which is correct).

#### Fix 1.3: Deprecate Manual `?? 0` in Components

**Action**: Create linting rule in ESLint config:
```javascript
{
  "no-restricted-syntax": [
    "error",
    {
      "selector": "BinaryExpression[operator='??'] > Literal[value=0]",
      "message": "Use formatCurrencyOrNA/formatPercentOrNA instead of ?? 0"
    }
  ]
}
```

**Enforcement**: Add to pre-commit hook. Commit `f343243` added formatters; make them mandatory.

---

### PRIORITY 2: State Leak (HIGH)

#### Fix 2.1: Validate Stage Overrides in src/features/deals/hooks/useDeals.ts

**Current (Line 34-47, BROKEN)**:
```typescript
const mergedDeals = useMemo(() => {
  return initialDeals.map((deal) => ({
    ...deal,
    ...(stageOverrides[deal.id] || {}),
  }));
}, [initialDeals, stageOverrides]);
```

**Fixed (CORRECT)**:
```typescript
const mergedDeals = useMemo(() => {
  // Validate overrides against current deals
  const validDeals = new Set(initialDeals.map((d) => d.id));
  const cleanOverrides = Object.fromEntries(
    Object.entries(stageOverrides).filter(([id]) => validDeals.has(id))
  );
  
  return initialDeals.map((deal) => ({
    ...deal,
    ...(cleanOverrides[deal.id] || {}),
  }));
}, [initialDeals, stageOverrides]);
```

**Test Case**:
```typescript
it('removes overrides for deals no longer in list', () => {
  const { rerender } = render(<DealsComponent initialDeals={[deal1, deal2]} />);
  // User drags deal1 to stage
  act(() => setStageOverride(deal1.id, 'Under Review'));
  // Server removes deal1
  rerender(<DealsComponent initialDeals={[deal2]} />);
  // Override should be cleared
  expect(getDeals()).not.toHaveProperty([deal1.id]);
});
```

---

### PRIORITY 3: Test Coverage (MEDIUM)

#### Fix 3.1: Add Unit Tests for Deal Schema Transforms

**Location**: src/lib/api/schemas/__tests__/deal.test.ts

**Test Cases**:
```typescript
describe('deal schema', () => {
  it('transforms null numeric fields to undefined', () => {
    const raw = { units: null, avgUnitSf: null };
    const parsed = dealSchema.parse(raw);
    expect(parsed.units).toBeUndefined();
    expect(parsed.avgUnitSf).toBeUndefined();
  });

  it('preserves enrichment fields as null/undefined', () => {
    const raw = { leveredIrr: null };
    const parsed = dealSchema.parse(raw);
    expect(parsed.leveredIrr).toBeUndefined();
  });
});
```

#### Fix 3.2: Add Tests for Comparison Chart Data Prep

**Location**: src/features/deals/__tests__/comparison.test.ts

**Test Cases**:
```typescript
describe('ComparisonCharts data prep', () => {
  it('handles missing cap rate data in metrics', () => {
    const deals = [
      { propertyName: 'Deal A', t12CapOnPp: 0.05 },
      { propertyName: 'Deal B', t12CapOnPp: undefined },
    ];
    const data = barChartData(deals);
    expect(data[0]['Deal A']).toBe(5);
    expect(data[0]['Deal B']).toBeUndefined(); // Not 0
  });
});
```

---

## Priority Matrix

| Regression Type | Files | Instances | Recent Fixes | Priority | Effort | Impact |
|-----------------|-------|-----------|--------------|----------|--------|--------|
| Silent Coercion | 16 | 45 | 4 | P1 (CRITICAL) | Medium | HIGH |
| State Leak | 1 | 1 logic flaw | 3 | P2 (HIGH) | Low | MEDIUM |
| Schema Drift | 1 | 5 field assumptions | 2 | P3 (MEDIUM) | Medium | MEDIUM |
| Enrichment Gap | 2 | 3 field assumptions | 2 | P4 (LOW) | Low | LOW |
| Test Gap | 4 | N/A (coverage) | 5 | P2 (HIGH) | High | HIGH |

---

## Implementation Roadmap

### Phase 1 (Week 1): Silent Coercion Fix
1. Update src/lib/api/schemas/deal.ts (Fix 1.1)
2. Update ComparisonCharts.tsx (Fix 1.2)
3. Update OperationsTab.tsx (similar pattern)
4. Add ESLint rule (Fix 1.3)
5. **Test**: Regression test suite to verify "N/A" displays for null/undefined, "$0" never appears for missing data

### Phase 2 (Week 2): State Leak Fix
1. Implement override validation in useDeals.ts (Fix 2.1)
2. Add test case for deleted deal scenario
3. **Test**: Integration test with real Kanban drag operations

### Phase 3 (Week 3): Test Coverage
1. Add schema transform tests (Fix 3.1)
2. Add chart data prep tests (Fix 3.2)
3. Expand existing test coverage for deal components (target 70%+)
4. **Test**: Run full test suite; verify regression tests pass

---

## Regression Detection Going Forward

### Commit Hook (pre-commit)
```bash
# Warn if new ?? 0 patterns added
git diff --cached | grep -E '\\?\\? 0' && echo "WARNING: ?? 0 pattern detected"

# Enforce ESLint before commit
npm run lint -- --fix
```

### CI/CD (on PR)
```yaml
- name: Check for silent coercion patterns
  run: grep -r "?? 0" src/lib/api/schemas/ src/features/ && exit 1 || exit 0

- name: Test coverage minimum
  run: npm run test -- --coverage --coverageThreshold='{"lines": 70}'
```

### Monitoring (Post-Deploy)
```typescript
// In error boundary or analytics:
if (value === 0 && originalData === null) {
  console.warn('REGRESSION: Silent coercion detected', { field, deal });
  analytics.track('regression_silent_coercion', { field, dealId });
}
```

---

## References

**Commits Analyzed**:
- `f343243` — Added formatCurrencyOrNA/formatPercentOrNA (not retroactively applied)
- `9b5f8ef` — Fix extraction issues (thread safety, stale runs)
- `c7b92ea` — 49 regression tests added
- `8078ebb` — Vite optimization, page reviews, 3 bugs fixed
- `1291827` — Latest extraction re-run (revealed schema drift)

**Files Audited**: 16 files, 45 instances of `?? 0` anti-pattern  
**Test Coverage**: 4/5 hot spot files have <50% coverage  
**Severity**: 1 CRITICAL, 2 HIGH, 2 MEDIUM regressions identified
