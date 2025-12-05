export type DealStage = 
  | 'lead' 
  | 'underwriting' 
  | 'loi' 
  | 'due_diligence' 
  | 'closing' 
  | 'closed_won' 
  | 'closed_lost';

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
  createdAt: Date;
  timeline: DealTimelineEvent[];
  notes?: string;
}

export const DEAL_STAGE_LABELS: Record<DealStage, string> = {
  lead: 'Lead',
  underwriting: 'Underwriting',
  loi: 'LOI',
  due_diligence: 'Due Diligence',
  closing: 'Closing',
  closed_won: 'Closed Won',
  closed_lost: 'Closed Lost',
};

export const DEAL_STAGE_COLORS: Record<DealStage, string> = {
  lead: 'bg-neutral-100 text-neutral-700 border-neutral-300',
  underwriting: 'bg-blue-100 text-blue-700 border-blue-300',
  loi: 'bg-purple-100 text-purple-700 border-purple-300',
  due_diligence: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  closing: 'bg-orange-100 text-orange-700 border-orange-300',
  closed_won: 'bg-green-100 text-green-700 border-green-300',
  closed_lost: 'bg-red-100 text-red-700 border-red-300',
};
