# Database Integration Implementation Plan

**Created:** 2026-01-13
**Status:** In Progress
**Current Integration:** ~40%
**Target:** 100%

---

## Executive Summary

This plan outlines the steps to fully integrate the B&R Capital Dashboard frontend with the FastAPI backend, removing all mock data dependencies and establishing real database-driven functionality.

---

## Phase 1: Quick Wins (1-2 hours)

### 1.1 Migrate DealsPage to Use Existing API Hook

**Current State:** DealsPage imports `mockDeals` directly instead of using `useDeals()` hook
**Effort:** 15 minutes
**Files to Modify:**
- `src/pages/DealsPage.tsx`

**Implementation:**
```typescript
// Remove
import { mockDeals } from '@/data/mockDeals';

// Add
import { useDeals } from '@/hooks/api/useDeals';

// In component
const { data: deals, isLoading, error } = useDeals();
```

### 1.2 Update useDeals Hook with Config Utility

**Current State:** useDeals doesn't have mock fallback pattern
**Effort:** 15 minutes
**Files to Modify:**
- `src/hooks/api/useDeals.ts`

---

## Phase 2: Transactions API (2-3 hours)

### 2.1 Backend: Create Transactions Endpoint

**Files to Create:**
- `backend/app/models/transaction.py`
- `backend/app/schemas/transaction.py`
- `backend/app/crud/transaction.py`
- `backend/app/api/v1/endpoints/transactions.py`

**Model Schema:**
```python
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(UUID, primary_key=True)
    property_id = Column(UUID, ForeignKey("properties.id"), nullable=True)
    type = Column(String)  # income, expense, distribution, capital_call
    category = Column(String)  # rent, maintenance, tax, etc.
    amount = Column(Numeric(15, 2))
    date = Column(Date)
    description = Column(Text)
    status = Column(String)  # pending, completed, cancelled
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**Endpoints:**
- `GET /api/v1/transactions/` - List with filters
- `GET /api/v1/transactions/{id}` - Get by ID
- `POST /api/v1/transactions/` - Create
- `PUT /api/v1/transactions/{id}` - Update
- `DELETE /api/v1/transactions/{id}` - Soft delete

### 2.2 Frontend: Create Transactions Integration

**Files to Create:**
- `src/lib/api/transactions.ts`
- `src/hooks/api/useTransactions.ts`

**Files to Modify:**
- `src/pages/TransactionsPage.tsx`
- `src/hooks/api/index.ts`

---

## Phase 3: Documents API (2-3 hours)

### 3.1 Backend: Create Documents Endpoint

**Files to Create:**
- `backend/app/models/document.py`
- `backend/app/schemas/document.py`
- `backend/app/crud/document.py`
- `backend/app/api/v1/endpoints/documents.py`

**Endpoints:**
- `GET /api/v1/documents/` - List with filters
- `GET /api/v1/documents/{id}` - Get by ID
- `POST /api/v1/documents/upload` - Upload file
- `GET /api/v1/documents/{id}/download` - Download file
- `PUT /api/v1/documents/{id}` - Update metadata
- `DELETE /api/v1/documents/{id}` - Soft delete

### 3.2 Frontend: Create Documents Integration

**Files to Create:**
- `src/lib/api/documents.ts`
- `src/hooks/api/useDocuments.ts`

---

## Phase 4: Market Data API (3-4 hours)

### 4.1 Backend: Create Market Data Endpoint

**Approach:** Aggregate stats from existing property data

**Endpoints:**
- `GET /api/v1/market/overview` - Market overview stats
- `GET /api/v1/market/submarkets` - Submarket breakdown
- `GET /api/v1/market/trends` - Market trends over time
- `GET /api/v1/market/comparables` - Property comparables

### 4.2 Frontend: Create Market Data Integration

**Files to Create:**
- `src/lib/api/market.ts`
- `src/hooks/api/useMarketData.ts`

---

## Phase 5: Interest Rates API (2-3 hours)

### 5.1 Backend: Create Interest Rates Endpoint

**External Integration:** FRED API for Treasury rates

**Endpoints:**
- `GET /api/v1/interest-rates/current` - Current key rates
- `GET /api/v1/interest-rates/yield-curve` - Treasury yield curve
- `GET /api/v1/interest-rates/historical` - Historical rates

### 5.2 Frontend: Update Interest Rates Hook

**Files to Modify:**
- `src/hooks/useInterestRates.ts`

---

## Phase 6: Reporting API (3-4 hours)

### 6.1 Backend: Create Reporting Endpoint

**Endpoints:**
- `GET /api/v1/reporting/templates` - List templates
- `POST /api/v1/reporting/templates` - Create template
- `PUT /api/v1/reporting/templates/{id}` - Update template
- `DELETE /api/v1/reporting/templates/{id}` - Delete template
- `POST /api/v1/reporting/generate` - Generate report

### 6.2 Frontend: Create Reporting Integration

**Files to Create:**
- `src/lib/api/reporting.ts`
- `src/hooks/api/useReporting.ts`

---

## Phase 7: Cleanup (1-2 hours)

### 7.1 Remove Mock Data Files

After all integrations complete:
- `src/data/mockDeals.ts`
- `src/data/mockTransactions.ts`
- `src/data/mockDocuments.ts`
- `src/data/mockMarketData.ts`
- `src/data/mockInterestRates.ts`
- `src/data/mockReportingData.ts`

---

## Timeline Summary

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Quick Wins | 1-2 hrs | HIGH |
| Phase 2: Transactions | 2-3 hrs | HIGH |
| Phase 3: Documents | 2-3 hrs | MEDIUM |
| Phase 4: Market Data | 3-4 hrs | MEDIUM |
| Phase 5: Interest Rates | 2-3 hrs | LOW |
| Phase 6: Reporting | 3-4 hrs | LOW |
| Phase 7: Cleanup | 1-2 hrs | FINAL |

**Total Estimate:** 15-21 hours

---

## Success Criteria

1. All frontend pages fetch data from real API
2. CRUD operations persist to database
3. No mock data imports in production code
4. VITE_USE_MOCK_DATA toggle works for all features
5. Error handling gracefully degrades
6. Performance < 500ms for list operations
