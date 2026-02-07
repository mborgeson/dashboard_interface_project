import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { backendDealSchema, dealsListResponseSchema } from '../deal';
import { mapBackendStage } from '../deal';

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
    total_equity_commitment: 5000000,
    ...overrides,
  };
}

describe('backendDealSchema', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('transforms a valid backend deal to frontend Deal type', () => {
    const result = backendDealSchema.parse(makeBackendDeal());

    expect(result.id).toBe('42');
    expect(result.propertyName).toBe('505 West (Tempe, AZ)');
    expect(result.address.street).toBe('505 West');
    expect(result.address.city).toBe('Tempe');
    expect(result.address.state).toBe('AZ');
    expect(result.value).toBe(15000000);
    expect(result.stage).toBe('initial_review');
    expect(result.createdAt).toBeInstanceOf(Date);
    expect(result.units).toBe(200);
    expect(result.avgUnitSf).toBe(900);
    expect(result.notes).toBe('Good opportunity');
  });

  it('parses asking_price as number', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({ asking_price: '25000000' }),
    );
    expect(result.value).toBe(25000000);
  });

  it('falls back to final_price when asking_price is null', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({ asking_price: null, final_price: '20000000' }),
    );
    expect(result.value).toBe(20000000);
  });

  it('defaults value to 0 when both prices are null', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({ asking_price: null, final_price: null }),
    );
    expect(result.value).toBe(0);
  });

  it('calculates daysInPipeline from created_at', () => {
    const result = backendDealSchema.parse(makeBackendDeal());
    const expected = Math.floor(
      (new Date('2025-06-01T00:00:00Z').getTime() -
        new Date('2025-01-15T10:00:00Z').getTime()) /
        86400000,
    );
    expect(result.daysInStage).toBe(expected);
    expect(result.totalDaysInPipeline).toBe(expected);
  });

  it('handles null optional enrichment fields', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({
        total_units: null,
        avg_unit_sf: null,
        current_owner: null,
        last_sale_price_per_unit: null,
        last_sale_date: null,
        t12_return_on_cost: null,
        levered_irr: null,
        levered_moic: null,
        total_equity_commitment: null,
      }),
    );
    expect(result.units).toBe(0);
    expect(result.avgUnitSf).toBe(0);
    expect(result.currentOwner).toBe('');
    expect(result.leveredIrr).toBe(0);
    expect(result.leveredMoic).toBe(0);
  });

  it('converts null notes to undefined', () => {
    const result = backendDealSchema.parse(makeBackendDeal({ notes: null }));
    expect(result.notes).toBeUndefined();
  });

  it('throws on missing required field', () => {
    const raw = makeBackendDeal();
    delete (raw as Record<string, unknown>).name;
    expect(() => backendDealSchema.parse(raw)).toThrow();
  });

  it('throws on wrong type for id', () => {
    expect(() =>
      backendDealSchema.parse(makeBackendDeal({ id: 'not-a-number' })),
    ).toThrow();
  });
});

describe('mapBackendStage', () => {
  it('maps identity stages', () => {
    expect(mapBackendStage('dead')).toBe('dead');
    expect(mapBackendStage('initial_review')).toBe('initial_review');
    expect(mapBackendStage('active_review')).toBe('active_review');
    expect(mapBackendStage('under_contract')).toBe('under_contract');
    expect(mapBackendStage('closed')).toBe('closed');
    expect(mapBackendStage('realized')).toBe('realized');
  });

  it('maps legacy stages to new stages', () => {
    expect(mapBackendStage('lead')).toBe('initial_review');
    expect(mapBackendStage('underwriting')).toBe('active_review');
    expect(mapBackendStage('loi_submitted')).toBe('under_contract');
    expect(mapBackendStage('due_diligence')).toBe('under_contract');
  });

  it('defaults unknown stages to initial_review', () => {
    expect(mapBackendStage('unknown_stage')).toBe('initial_review');
  });
});

describe('parseCityState via schema transform', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('parses city and state from "Name (City, ST)" format', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({ name: 'The Villas (Scottsdale, AZ)' }),
    );
    expect(result.address.street).toBe('The Villas');
    expect(result.address.city).toBe('Scottsdale');
    expect(result.address.state).toBe('AZ');
  });

  it('handles name without city/state pattern', () => {
    const result = backendDealSchema.parse(
      makeBackendDeal({ name: 'Simple Property Name' }),
    );
    expect(result.address.street).toBe('Simple Property Name');
    expect(result.address.city).toBe('');
    expect(result.address.state).toBe('');
  });
});

describe('dealsListResponseSchema', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('parses a list response with items and total', () => {
    const raw = { items: [makeBackendDeal()], total: 1 };
    const result = dealsListResponseSchema.parse(raw);
    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.items[0].id).toBe('42');
  });

  it('parses empty list', () => {
    const raw = { items: [], total: 0 };
    const result = dealsListResponseSchema.parse(raw);
    expect(result.items).toHaveLength(0);
    expect(result.total).toBe(0);
  });
});
