# Wave 3 Resumption Instructions

**Previous Wave:** Wave 2 Complete
**Commit:** `ed93c06` - feat: complete Wave 2 database integration (Phases 4 & 6)
**Date:** 2026-01-13

---

## Quick Start Prompt

Copy and paste this into a new Claude Code terminal:

```
Resume Wave 3 for B&R Capital Dashboard database integration project.

## Current State (commit ed93c06)
- Wave 1 & 2 COMPLETE: All 6 phases implemented
- Phases: Deals, Transactions, Documents, Market Data, Interest Rates, Reporting
- Database: Migrations created (apply with `alembic upgrade head`)
- Build: TypeScript and frontend build passing

## Immediate Tasks (Wave 3 - Phase 7: Cleanup)
1. Apply pending migration for reporting tables
2. Test all Wave 2 endpoints (Market Data + Reporting)
3. Identify and remove mock data file imports
4. Update any pages still using mock data directly
5. Final integration testing

## Reference Files
- Plan: docs/plans/database-integration-plan.md
- Wave 2 Checkpoint: docs/checkpoints/wave2-complete-checkpoint.md
- Resumption: docs/checkpoints/wave3-resumption-instructions.md
- Hook patterns: src/hooks/api/useDeals.ts

## Agent Swarm Setup for Wave 3

Initialize a mesh topology swarm for parallel cleanup operations:

### Swarm Configuration
```javascript
// Initialize swarm for cleanup tasks
mcp__claude-flow__swarm_init({
  topology: "mesh",
  maxAgents: 5,
  sessionId: "wave3-cleanup"
})

// Spawn specialized agents in parallel
Task("Mock Data Researcher", "Search codebase for all mock data imports and usages. Files: src/data/mock*.ts, src/pages/*.tsx, src/components/**/*.tsx. Output list of files still using mock imports.", "researcher")

Task("Deals/Transactions Cleanup", "Remove mock imports from DealsPage, TransactionsPage. Ensure using useDeals, useTransactions hooks. Test with VITE_USE_MOCK_DATA=false.", "coder")

Task("Market/Reporting Cleanup", "Remove mock imports from MarketPage, ReportingPage. Ensure using useMarketData, useReporting hooks. Test integration.", "coder")

Task("Integration Tester", "Run frontend with VITE_USE_MOCK_DATA=false. Test all pages load correctly. Document any errors.", "tester")

Task("Code Reviewer", "Review cleanup changes. Verify no remaining mock imports in production code. Check for TypeScript errors.", "reviewer")
```

## Mock Data Files to Review

These files may need cleanup (verify before deletion):
- src/data/mockDeals.ts
- src/data/mockTransactions.ts
- src/data/mockDocuments.ts
- src/data/mockMarketData.ts
- src/data/mockInterestRates.ts
- src/data/mockReportingData.ts
- src/data/mockProperties.ts

## API Endpoints to Test

### Wave 2 Endpoints (new)
```bash
# Market Data
curl http://localhost:8000/api/v1/market/overview | jq
curl http://localhost:8000/api/v1/market/submarkets | jq
curl http://localhost:8000/api/v1/market/trends | jq
curl http://localhost:8000/api/v1/market/comparables | jq

# Reporting
curl http://localhost:8000/api/v1/reporting/templates | jq
curl http://localhost:8000/api/v1/reporting/queue | jq
curl http://localhost:8000/api/v1/reporting/schedules | jq
curl http://localhost:8000/api/v1/reporting/widgets | jq
```

### Wave 1 Endpoints (verify still working)
```bash
curl http://localhost:8000/api/v1/transactions/ | jq
curl http://localhost:8000/api/v1/documents/ | jq
curl http://localhost:8000/api/v1/interest-rates/current | jq
```

## Success Criteria for Wave 3

1. [ ] All migrations applied successfully
2. [ ] All API endpoints responding correctly
3. [ ] No mock data imports in page components
4. [ ] Frontend works with `VITE_USE_MOCK_DATA=false`
5. [ ] TypeScript compilation passes
6. [ ] Frontend build passes
7. [ ] Mock data files can be safely archived/removed

## Memory Checkpoint

To retrieve Wave 2 context:
```bash
mcp-cli call claude-mem/chroma_query_documents '{
  "collection_name": "claude_memories",
  "query_texts": ["dashboard_interface_project wave2 database integration checkpoint"],
  "n_results": 3
}'
```
```

---

## Full Context Restoration

If more context is needed, read these files in order:
1. `docs/plans/database-integration-plan.md` - Full integration plan
2. `docs/checkpoints/wave1-complete-checkpoint.md` - Wave 1 details
3. `docs/checkpoints/wave2-complete-checkpoint.md` - Wave 2 details
4. `src/hooks/api/index.ts` - All available API hooks
