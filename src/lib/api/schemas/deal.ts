/**
 * Zod schemas for deal API responses
 *
 * Validates the raw backend deal JSON (snake_case, numeric strings)
 * and transforms to frontend Deal type. Replaces transformBackendDeal(),
 * parseCityState(), mapBackendStage(), and BackendDealResponse interface.
 */
import { z } from 'zod';
import type { Deal } from '@/types/deal';

// ---------- Helpers ----------

const STAGE_MAP: Record<string, Deal['stage']> = {
  dead: 'dead',
  initial_review: 'initial_review',
  active_review: 'active_review',
  under_contract: 'under_contract',
  closed: 'closed',
  realized: 'realized',
  // Legacy 8-stage backwards compat
  lead: 'initial_review',
  underwriting: 'active_review',
  loi_submitted: 'under_contract',
  due_diligence: 'under_contract',
};

export function mapBackendStage(stage: string): Deal['stage'] {
  return STAGE_MAP[stage] ?? 'initial_review';
}

function parseCityState(name: string): { propertyName: string; city: string; state: string } {
  const match = name.match(/^(.+?)\s*\(([^,]+),\s*([A-Z]{2})\)\s*(?:\(\d{4}\))?$/);
  if (match) {
    return { propertyName: match[1].trim(), city: match[2].trim(), state: match[3].trim() };
  }
  return { propertyName: name, city: '', state: '' };
}

// ---------- Backend deal schema ----------

export const backendDealSchema = z
  .object({
    id: z.number(),
    name: z.string(),
    deal_type: z.string(),
    property_id: z.number().nullable(),
    assigned_user_id: z.number().nullable(),
    stage: z.string(),
    stage_order: z.number(),
    asking_price: z.string().nullable(),
    offer_price: z.string().nullable(),
    final_price: z.string().nullable(),
    projected_irr: z.string().nullable(),
    projected_coc: z.string().nullable(),
    projected_equity_multiple: z.string().nullable(),
    hold_period_years: z.number().nullable(),
    initial_contact_date: z.string().nullable(),
    actual_close_date: z.string().nullable(),
    source: z.string().nullable(),
    broker_name: z.string().nullable(),
    notes: z.string().nullable(),
    investment_thesis: z.string().nullable(),
    deal_score: z.number().nullable(),
    priority: z.string().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
    // Enrichment fields
    total_units: z.number().nullable(),
    avg_unit_sf: z.number().nullable(),
    current_owner: z.string().nullable(),
    last_sale_price_per_unit: z.number().nullable(),
    last_sale_date: z.string().nullable(),
    t12_return_on_cost: z.number().nullable(),
    levered_irr: z.number().nullable(),
    levered_moic: z.number().nullable(),
    total_equity_commitment: z.number().nullable(),
  })
  .transform((d): Deal => {
    const { propertyName, city, state } = parseCityState(d.name);
    const value = d.asking_price
      ? parseFloat(d.asking_price)
      : d.final_price
        ? parseFloat(d.final_price)
        : 0;
    const now = new Date();
    const created = new Date(d.created_at);
    const daysInPipeline = Math.max(
      0,
      Math.floor((now.getTime() - created.getTime()) / 86400000),
    );

    return {
      id: String(d.id),
      propertyName: d.name,
      address: { street: propertyName, city, state },
      value,
      capRate: 0,
      stage: mapBackendStage(d.stage),
      daysInStage: daysInPipeline,
      totalDaysInPipeline: daysInPipeline,
      assignee: '',
      propertyType: d.deal_type || 'acquisition',
      units: d.total_units ?? 0,
      avgUnitSf: d.avg_unit_sf ?? 0,
      currentOwner: d.current_owner ?? '',
      lastSalePricePerUnit: d.last_sale_price_per_unit ?? 0,
      lastSaleDate: d.last_sale_date ?? '',
      t12ReturnOnCost: d.t12_return_on_cost ?? 0,
      leveredIrr: d.levered_irr ?? 0,
      leveredMoic: d.levered_moic ?? 0,
      totalEquityCommitment: d.total_equity_commitment ?? 0,
      createdAt: created,
      timeline: [],
      notes: d.notes ?? undefined,
    };
  });

// ---------- Response schemas ----------

export const dealsListResponseSchema = z.object({
  items: z.array(backendDealSchema),
  total: z.number(),
});
