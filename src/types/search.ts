import type { Property } from './property';
import type { Deal } from './deal';
import type { Document } from './document';
import type { Transaction } from './transaction';

export interface SearchResult {
  type: 'property' | 'deal' | 'document' | 'transaction';
  id: string;
  title: string;
  subtitle: string;
  matchedField?: string;
  category?: string;
  metadata?: {
    value?: string;
    amount?: string;
    date?: string;
    property?: string;
  };
  item: Property | Deal | Document | Transaction;
}
