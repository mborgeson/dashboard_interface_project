export interface Transaction {
  id: string;
  propertyId: string;
  propertyName: string;
  date: Date;
  type: 'acquisition' | 'disposition' | 'capital_improvement' | 'refinance' | 'distribution';
  amount: number;
  description: string;
  category?: string;
  documents?: string[];
}
