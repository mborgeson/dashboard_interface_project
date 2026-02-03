export type DealStage =
  | 'dead'
  | 'initial_review'
  | 'active_review'
  | 'under_contract'
  | 'closed'
  | 'realized';

export interface DealTimelineEvent {
  id: string;
  date: Date;
  stage: DealStage;
  description: string;
  user?: string;
}

export interface Deal {
  id: string;
  propertyName: string;
  address: {
    street: string;
    city: string;
    state: string;
  };
  value: number;
  capRate: number;
  stage: DealStage;
  daysInStage: number;
  totalDaysInPipeline: number;
  assignee: string;
  propertyType: string;
  units: number;
  avgUnitSf: number;
  currentOwner: string;
  lastSalePricePerUnit: number;
  lastSaleDate: string;
  t12ReturnOnCost: number;
  leveredIrr: number;
  leveredMoic: number;
  totalEquityCommitment: number;
  createdAt: Date;
  timeline: DealTimelineEvent[];
  notes?: string;
}

export const DEAL_STAGE_LABELS: Record<DealStage, string> = {
  dead: 'Dead Deals',
  initial_review: 'Initial UW and Review',
  active_review: 'Active UW and Review',
  under_contract: 'Deals Under Contract',
  closed: 'Closed Deals',
  realized: 'Realized Deals',
};

export const DEAL_STAGE_COLORS: Record<DealStage, string> = {
  dead: 'bg-red-100 text-red-700 border-red-300',
  initial_review: 'bg-blue-100 text-blue-700 border-blue-300',
  active_review: 'bg-purple-100 text-purple-700 border-purple-300',
  under_contract: 'bg-orange-100 text-orange-700 border-orange-300',
  closed: 'bg-green-100 text-green-700 border-green-300',
  realized: 'bg-emerald-100 text-emerald-700 border-emerald-300',
};
