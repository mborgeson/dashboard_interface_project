export type TransactionType = 'acquisition' | 'disposition' | 'capital_improvement' | 'refinance' | 'distribution';

export interface Transaction {
  id: string;
  propertyId: string;
  propertyName: string;
  date: Date;
  type: TransactionType;
  amount: number;
  description: string;
  category?: string;
  documents?: string[];
}
