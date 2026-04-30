import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  dealCursorPaginatedResponseSchema,
  proformaFieldValueSchema,
  proformaFieldGroupSchema,
  proformaReturnsResponseSchema,
  watchlistStatusResponseSchema,
  stageChangeLogResponseSchema,
  stageHistoryResponseSchema,
  kanbanBoardResponseSchema,
  stageMappingResponseSchema,
  manualStageOverrideSchema,
} from '../deal';

// ---------- Shared fixtures ----------

function makeBackendDeal(overrides: Record<string, unknown> = {}) {
  return {
    id: 42,
    name: '505 West (Tempe, AZ)',
    deal_type: 'acquisition',
    property_id: null,
    assigned_user_id: null,
    stage: 'initial_review',
    stage_order: 1,
    asking_price: '15000000',
    offer_price: null,
    final_price: null,
    projected_irr: '0.18',
    projected_coc: '0.08',
    projected_equity_multiple: '2.1',
    hold_period_years: 5,
    initial_contact_date: null,
    actual_close_date: null,
    source: 'broker',
    broker_name: 'John Smith',
    notes: 'Good opportunity',
    investment_thesis: null,
    deal_score: 85,
    priority: 'high',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-02-01T12:00:00Z',
    total_units: 200,
    avg_unit_sf: 900,
    current_owner: 'ABC Holdings',
    last_sale_price_per_unit: 180000,
    last_sale_date: '2020-06-15',
    t12_return_on_cost: 0.065,
    levered_irr: 0.18,
    levered_moic: 2.1,
    stage_updated_at: null,
    total_equity_commitment: 5000000,
    ...overrides,
  };
}

function makeStageChangeLog(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    deal_id: 42,
    old_stage: 'initial_review',
    new_stage: 'active_review',
    source: 'manual',
    changed_by_user_id: 7,
    reason: 'Promoted after underwriting',
    created_at: '2025-03-01T10:00:00Z',
    ...overrides,
  };
}

// ---------- dealCursorPaginatedResponseSchema ----------

describe('dealCursorPaginatedResponseSchema', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('parses a cursor-paginated response with cursors and total', () => {
    const raw = {
      items: [makeBackendDeal()],
      next_cursor: 'cursor-abc',
      prev_cursor: 'cursor-xyz',
      has_more: true,
      total: 25,
    };
    const result = dealCursorPaginatedResponseSchema.parse(raw);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].id).toBe('42');
    expect(result.next_cursor).toBe('cursor-abc');
    expect(result.prev_cursor).toBe('cursor-xyz');
    expect(result.has_more).toBe(true);
    expect(result.total).toBe(25);
  });

  it('accepts null cursors when there are no more pages', () => {
    const raw = {
      items: [makeBackendDeal()],
      next_cursor: null,
      prev_cursor: null,
      has_more: false,
      total: null,
    };
    const result = dealCursorPaginatedResponseSchema.parse(raw);
    expect(result.next_cursor).toBeNull();
    expect(result.prev_cursor).toBeNull();
    expect(result.has_more).toBe(false);
    expect(result.total).toBeNull();
  });

  it('accepts payload with optional cursors and total omitted entirely', () => {
    const raw = { items: [], has_more: false };
    const result = dealCursorPaginatedResponseSchema.parse(raw);
    expect(result.items).toHaveLength(0);
    expect(result.has_more).toBe(false);
    expect(result.next_cursor).toBeUndefined();
    expect(result.prev_cursor).toBeUndefined();
    expect(result.total).toBeUndefined();
  });

  it('throws when has_more is missing', () => {
    expect(() =>
      dealCursorPaginatedResponseSchema.parse({ items: [] }),
    ).toThrow();
  });
});

// ---------- proformaFieldValueSchema ----------

describe('proformaFieldValueSchema', () => {
  it('transforms snake_case to camelCase with both numeric and text values', () => {
    const result = proformaFieldValueSchema.parse({
      field_name: 'noi',
      value_numeric: 1250000.5,
      value_text: '1,250,000.50',
    });
    expect(result.fieldName).toBe('noi');
    expect(result.valueNumeric).toBe(1250000.5);
    expect(result.valueText).toBe('1,250,000.50');
  });

  it('coerces null numeric and text values to undefined', () => {
    const result = proformaFieldValueSchema.parse({
      field_name: 'cap_rate',
      value_numeric: null,
      value_text: null,
    });
    expect(result.fieldName).toBe('cap_rate');
    expect(result.valueNumeric).toBeUndefined();
    expect(result.valueText).toBeUndefined();
  });

  it('accepts payload with optional value fields entirely missing', () => {
    const result = proformaFieldValueSchema.parse({ field_name: 'irr' });
    expect(result.fieldName).toBe('irr');
    expect(result.valueNumeric).toBeUndefined();
    expect(result.valueText).toBeUndefined();
  });

  it('preserves zero numeric values without converting to undefined', () => {
    const result = proformaFieldValueSchema.parse({
      field_name: 'vacancy',
      value_numeric: 0,
    });
    expect(result.valueNumeric).toBe(0);
  });
});

// ---------- proformaFieldGroupSchema ----------

describe('proformaFieldGroupSchema', () => {
  it('parses a category with a list of transformed fields', () => {
    const result = proformaFieldGroupSchema.parse({
      category: 'returns',
      fields: [
        { field_name: 'irr', value_numeric: 0.18, value_text: null },
        { field_name: 'moic', value_numeric: 2.1, value_text: null },
      ],
    });
    expect(result.category).toBe('returns');
    expect(result.fields).toHaveLength(2);
    expect(result.fields[0].fieldName).toBe('irr');
    expect(result.fields[0].valueNumeric).toBe(0.18);
    expect(result.fields[1].fieldName).toBe('moic');
  });

  it('accepts an empty fields array', () => {
    const result = proformaFieldGroupSchema.parse({
      category: 'misc',
      fields: [],
    });
    expect(result.category).toBe('misc');
    expect(result.fields).toHaveLength(0);
  });

  it('throws when category is missing', () => {
    expect(() =>
      proformaFieldGroupSchema.parse({ fields: [] }),
    ).toThrow();
  });
});

// ---------- proformaReturnsResponseSchema ----------

describe('proformaReturnsResponseSchema', () => {
  it('transforms deal identifiers to camelCase and preserves groups', () => {
    const result = proformaReturnsResponseSchema.parse({
      deal_id: 42,
      deal_name: '505 West',
      groups: [
        {
          category: 'returns',
          fields: [
            { field_name: 'irr', value_numeric: 0.18 },
          ],
        },
      ],
      total: 1,
    });
    expect(result.dealId).toBe(42);
    expect(result.dealName).toBe('505 West');
    expect(result.total).toBe(1);
    expect(result.groups).toHaveLength(1);
    expect(result.groups[0].category).toBe('returns');
    expect(result.groups[0].fields[0].fieldName).toBe('irr');
  });

  it('parses an empty groups array with zero total', () => {
    const result = proformaReturnsResponseSchema.parse({
      deal_id: 42,
      deal_name: '505 West',
      groups: [],
      total: 0,
    });
    expect(result.dealId).toBe(42);
    expect(result.groups).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it('throws when deal_id is missing', () => {
    expect(() =>
      proformaReturnsResponseSchema.parse({
        deal_name: '505 West',
        groups: [],
        total: 0,
      }),
    ).toThrow();
  });
});

// ---------- watchlistStatusResponseSchema ----------

describe('watchlistStatusResponseSchema', () => {
  it('transforms snake_case to camelCase when watched', () => {
    const result = watchlistStatusResponseSchema.parse({
      deal_id: 42,
      is_watched: true,
    });
    expect(result.dealId).toBe(42);
    expect(result.isWatched).toBe(true);
  });

  it('transforms snake_case to camelCase when not watched', () => {
    const result = watchlistStatusResponseSchema.parse({
      deal_id: 99,
      is_watched: false,
    });
    expect(result.dealId).toBe(99);
    expect(result.isWatched).toBe(false);
  });

  it('throws when is_watched is missing', () => {
    expect(() =>
      watchlistStatusResponseSchema.parse({ deal_id: 42 }),
    ).toThrow();
  });

  it('throws when deal_id has wrong type', () => {
    expect(() =>
      watchlistStatusResponseSchema.parse({
        deal_id: 'forty-two',
        is_watched: true,
      }),
    ).toThrow();
  });
});

// ---------- stageChangeLogResponseSchema ----------

describe('stageChangeLogResponseSchema', () => {
  it('transforms a fully populated stage change log entry', () => {
    const result = stageChangeLogResponseSchema.parse(makeStageChangeLog());
    expect(result.id).toBe(1);
    expect(result.dealId).toBe(42);
    expect(result.oldStage).toBe('initial_review');
    expect(result.newStage).toBe('active_review');
    expect(result.source).toBe('manual');
    expect(result.changedByUserId).toBe(7);
    expect(result.reason).toBe('Promoted after underwriting');
    expect(result.createdAt).toBe('2025-03-01T10:00:00Z');
  });

  it('coerces null optional fields to undefined', () => {
    const result = stageChangeLogResponseSchema.parse(
      makeStageChangeLog({
        old_stage: null,
        changed_by_user_id: null,
        reason: null,
      }),
    );
    expect(result.oldStage).toBeUndefined();
    expect(result.changedByUserId).toBeUndefined();
    expect(result.reason).toBeUndefined();
  });

  it('accepts payload with optional fields entirely missing (system-generated change)', () => {
    const result = stageChangeLogResponseSchema.parse({
      id: 2,
      deal_id: 42,
      new_stage: 'closed',
      source: 'system',
      created_at: '2025-04-01T10:00:00Z',
    });
    expect(result.id).toBe(2);
    expect(result.newStage).toBe('closed');
    expect(result.source).toBe('system');
    expect(result.oldStage).toBeUndefined();
    expect(result.changedByUserId).toBeUndefined();
    expect(result.reason).toBeUndefined();
  });

  it('throws when new_stage is missing', () => {
    const raw = makeStageChangeLog();
    delete (raw as Record<string, unknown>).new_stage;
    expect(() => stageChangeLogResponseSchema.parse(raw)).toThrow();
  });
});

// ---------- stageHistoryResponseSchema ----------

describe('stageHistoryResponseSchema', () => {
  it('transforms a history payload with multiple entries', () => {
    const result = stageHistoryResponseSchema.parse({
      deal_id: 42,
      history: [
        makeStageChangeLog(),
        makeStageChangeLog({
          id: 2,
          new_stage: 'under_contract',
          old_stage: 'active_review',
        }),
      ],
      total: 2,
    });
    expect(result.dealId).toBe(42);
    expect(result.total).toBe(2);
    expect(result.history).toHaveLength(2);
    expect(result.history[0].newStage).toBe('active_review');
    expect(result.history[1].newStage).toBe('under_contract');
    expect(result.history[1].oldStage).toBe('active_review');
  });

  it('parses an empty history array', () => {
    const result = stageHistoryResponseSchema.parse({
      deal_id: 42,
      history: [],
      total: 0,
    });
    expect(result.dealId).toBe(42);
    expect(result.history).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it('throws when total is missing', () => {
    expect(() =>
      stageHistoryResponseSchema.parse({ deal_id: 42, history: [] }),
    ).toThrow();
  });
});

// ---------- kanbanBoardResponseSchema ----------

describe('kanbanBoardResponseSchema', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('transforms a board with deals grouped by stage', () => {
    const result = kanbanBoardResponseSchema.parse({
      stages: {
        initial_review: [makeBackendDeal()],
        active_review: [makeBackendDeal({ id: 43, stage: 'active_review' })],
      },
      total_deals: 2,
      stage_counts: { initial_review: 1, active_review: 1 },
    });
    expect(result.totalDeals).toBe(2);
    expect(result.stageCounts).toEqual({ initial_review: 1, active_review: 1 });
    expect(result.stages.initial_review).toHaveLength(1);
    expect(result.stages.initial_review[0].id).toBe('42');
    expect(result.stages.active_review[0].id).toBe('43');
  });

  it('transforms a board with empty stage buckets', () => {
    const result = kanbanBoardResponseSchema.parse({
      stages: {
        initial_review: [],
        dead: [],
      },
      total_deals: 0,
      stage_counts: { initial_review: 0, dead: 0 },
    });
    expect(result.totalDeals).toBe(0);
    expect(result.stages.initial_review).toHaveLength(0);
    expect(result.stages.dead).toHaveLength(0);
  });

  it('throws when stage_counts is missing', () => {
    expect(() =>
      kanbanBoardResponseSchema.parse({
        stages: {},
        total_deals: 0,
      }),
    ).toThrow();
  });
});

// ---------- stageMappingResponseSchema ----------

describe('stageMappingResponseSchema', () => {
  it('transforms folder_to_stage to folderToStage and preserves stages', () => {
    const result = stageMappingResponseSchema.parse({
      stages: ['initial_review', 'active_review', 'under_contract', 'closed'],
      folder_to_stage: {
        '0) Initial Review': 'initial_review',
        '1) Active Review': 'active_review',
      },
    });
    expect(result.stages).toEqual([
      'initial_review',
      'active_review',
      'under_contract',
      'closed',
    ]);
    expect(result.folderToStage).toEqual({
      '0) Initial Review': 'initial_review',
      '1) Active Review': 'active_review',
    });
  });

  it('parses an empty mapping', () => {
    const result = stageMappingResponseSchema.parse({
      stages: [],
      folder_to_stage: {},
    });
    expect(result.stages).toHaveLength(0);
    expect(result.folderToStage).toEqual({});
  });

  it('throws when folder_to_stage is missing', () => {
    expect(() =>
      stageMappingResponseSchema.parse({ stages: [] }),
    ).toThrow();
  });
});

// ---------- manualStageOverrideSchema ----------

describe('manualStageOverrideSchema', () => {
  it('parses a manual stage override request with a reason', () => {
    const result = manualStageOverrideSchema.parse({
      stage: 'active_review',
      reason: 'Manual promotion after broker call',
    });
    expect(result.stage).toBe('active_review');
    expect(result.reason).toBe('Manual promotion after broker call');
  });

  it('accepts a null reason', () => {
    const result = manualStageOverrideSchema.parse({
      stage: 'dead',
      reason: null,
    });
    expect(result.stage).toBe('dead');
    expect(result.reason).toBeNull();
  });

  it('accepts payload with reason entirely missing', () => {
    const result = manualStageOverrideSchema.parse({ stage: 'closed' });
    expect(result.stage).toBe('closed');
    expect(result.reason).toBeUndefined();
  });

  it('throws when stage is missing', () => {
    expect(() => manualStageOverrideSchema.parse({})).toThrow();
  });
});
