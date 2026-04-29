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
    version: z.number().optional(),
    name: z.string(),
    deal_type: z.string(),
    property_id: z.number().nullable(),
    assigned_user_id: z.number().nullable(),
    stage: z.string(),
    stage_order: z.number(),
    asking_price: z.union([z.string(), z.number()]).nullable(),
    offer_price: z.union([z.string(), z.number()]).nullable(),
    final_price: z.union([z.string(), z.number()]).nullable(),
    projected_irr: z.union([z.string(), z.number()]).nullable(),
    projected_coc: z.union([z.string(), z.number()]).nullable(),
    projected_equity_multiple: z.union([z.string(), z.number()]).nullable(),
    hold_period_years: z.number().nullable(),
    initial_contact_date: z.string().nullable(),
    loi_submitted_date: z.string().nullable().optional(),
    due_diligence_start: z.string().nullable().optional(),
    due_diligence_end: z.string().nullable().optional(),
    target_close_date: z.string().nullable().optional(),
    actual_close_date: z.string().nullable(),
    source: z.string().nullable(),
    broker_name: z.string().nullable(),
    broker_company: z.string().nullable().optional(),
    competition_level: z.string().nullable().optional(),
    notes: z.string().nullable(),
    investment_thesis: z.string().nullable(),
    key_risks: z.string().nullable().optional(),
    documents: z.array(z.unknown()).nullable().optional(),
    activity_log: z.array(z.unknown()).nullable().optional(),
    tags: z.array(z.string()).nullable().optional(),
    custom_fields: z.record(z.string(), z.unknown()).nullable().optional(),
    deal_score: z.number().nullable(),
    priority: z.string().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
    stage_updated_at: z.string().nullable(),
    // Enrichment fields
    total_units: z.number().nullable(),
    avg_unit_sf: z.number().nullable(),
    current_owner: z.string().nullable(),
    last_sale_price_per_unit: z.number().nullable(),
    last_sale_date: z.string().nullable(),
    t12_return_on_cost: z.number().nullable(),
    levered_irr: z.number().nullable().optional(),
    levered_moic: z.number().nullable().optional(),
    total_equity_commitment: z.number().nullable(),
    // New enrichment fields
    property_city: z.string().nullable().optional(),
    submarket: z.string().nullable().optional(),
    year_built: z.number().nullable().optional(),
    year_renovated: z.number().nullable().optional(),
    vacancy_rate: z.number().nullable().optional(),
    bad_debt_rate: z.number().nullable().optional(),
    other_loss_rate: z.number().nullable().optional(),
    concessions_rate: z.number().nullable().optional(),
    noi_margin: z.number().nullable().optional(),
    purchase_price_extracted: z.number().nullable().optional(),
    total_acquisition_budget: z.number().nullable().optional(),
    basis_per_unit: z.number().nullable().optional(),
    t12_cap_on_pp: z.number().nullable().optional(),
    t3_cap_on_pp: z.number().nullable().optional(),
    total_cost_cap_t12: z.number().nullable().optional(),
    total_cost_cap_t3: z.number().nullable().optional(),
    loan_amount: z.number().nullable().optional(),
    lp_equity: z.number().nullable().optional(),
    exit_months: z.number().nullable().optional(),
    exit_cap_rate: z.number().nullable().optional(),
    unlevered_irr: z.number().nullable().optional(),
    unlevered_moic: z.number().nullable().optional(),
    lp_irr: z.number().nullable().optional(),
    lp_moic: z.number().nullable().optional(),
    latitude: z.number().nullable().optional(),
    longitude: z.number().nullable().optional(),
    recent_activities: z.array(z.object({
      action: z.string(),
      description: z.string(),
      created_at: z.string(),
    })).nullable().optional(),
  })
  .transform((d): Deal => {
    const { propertyName, city, state } = parseCityState(d.name);
    const value = d.asking_price
      ? (typeof d.asking_price === 'number' ? d.asking_price : parseFloat(d.asking_price))
      : d.final_price
        ? (typeof d.final_price === 'number' ? d.final_price : parseFloat(d.final_price))
        : 0;
    const now = new Date();
    const created = new Date(d.created_at);
    const daysInPipeline = Math.max(
      0,
      Math.floor((now.getTime() - created.getTime()) / 86400000),
    );
    const stageStart = d.stage_updated_at ? new Date(d.stage_updated_at) : created;
    const daysInStage = Math.max(
      0,
      Math.floor((now.getTime() - stageStart.getTime()) / 86400000),
    );

    return {
      id: String(d.id),
      propertyName: d.name,
      address: { street: propertyName, city, state },
      value,
      capRate: 0,
      stage: mapBackendStage(d.stage),
      daysInStage,
      totalDaysInPipeline: daysInPipeline,
      assignee: '',
      propertyType: d.deal_type || 'acquisition',
      units: d.total_units ?? undefined,
      avgUnitSf: d.avg_unit_sf ?? undefined,
      currentOwner: d.current_owner ?? undefined,
      lastSalePricePerUnit: d.last_sale_price_per_unit ?? undefined,
      lastSaleDate: d.last_sale_date ?? undefined,
      t12ReturnOnCost: d.t12_return_on_cost ?? undefined,
      leveredIrr: d.levered_irr ?? undefined,
      leveredMoic: d.levered_moic ?? undefined,
      totalEquityCommitment: d.total_equity_commitment ?? undefined,
      createdAt: created,
      timeline: [],
      notes: d.notes ?? undefined,
      // New enrichment fields
      propertyCity: d.property_city ?? undefined,
      submarket: d.submarket ?? undefined,
      yearBuilt: d.year_built ?? undefined,
      yearRenovated: d.year_renovated ?? undefined,
      vacancyRate: d.vacancy_rate ?? undefined,
      badDebtRate: d.bad_debt_rate ?? undefined,
      otherLossRate: d.other_loss_rate ?? undefined,
      concessionsRate: d.concessions_rate ?? undefined,
      noiMargin: d.noi_margin ?? undefined,
      purchasePrice: d.purchase_price_extracted ?? undefined,
      totalAcquisitionBudget: d.total_acquisition_budget ?? undefined,
      basisPerUnit: d.basis_per_unit ?? undefined,
      t12CapOnPp: d.t12_cap_on_pp ?? undefined,
      t3CapOnPp: d.t3_cap_on_pp ?? undefined,
      totalCostCapT12: d.total_cost_cap_t12 ?? undefined,
      totalCostCapT3: d.total_cost_cap_t3 ?? undefined,
      loanAmount: d.loan_amount ?? undefined,
      lpEquity: d.lp_equity ?? undefined,
      exitMonths: d.exit_months ?? undefined,
      exitCapRate: d.exit_cap_rate ?? undefined,
      unleveredIrr: d.unlevered_irr ?? undefined,
      unleveredMoic: d.unlevered_moic ?? undefined,
      lpIrr: d.lp_irr ?? undefined,
      lpMoic: d.lp_moic ?? undefined,
      latitude: d.latitude ?? undefined,
      longitude: d.longitude ?? undefined,
      recentActivities: d.recent_activities?.map((a) => ({
        action: a.action,
        description: a.description,
        createdAt: new Date(a.created_at),
      })) ?? undefined,
    };
  });

// ---------- Response schemas ----------

export const dealsListResponseSchema = z.object({
  items: z.array(backendDealSchema),
  total: z.number(),
});
