/**
 * Reporting Suite type definitions.
 *
 * Extracted from src/data/mockReportingData.ts (C-TD-016) so that
 * types can be imported independently of mock data.
 */

export interface ReportTemplateParameter {
  name: string;
  label: string;
  description?: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'select' | 'multiselect';
  required: boolean;
  defaultValue?: unknown;
  options?: string[];
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  category: 'executive' | 'financial' | 'market' | 'portfolio' | 'custom';
  thumbnail?: string;
  sections: string[];
  lastModified: string;
  createdBy: string;
  isDefault: boolean;
  supportedFormats: ('pdf' | 'excel' | 'pptx')[];
  parameters: ReportTemplateParameter[];
}

export interface QueuedReport {
  id: string;
  name: string;
  templateId: string;
  templateName: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  progress: number;
  requestedBy: string;
  requestedAt: string;
  completedAt?: string;
  format: 'pdf' | 'excel' | 'pptx';
  fileSize?: string;
  downloadUrl?: string;
  error?: string;
}

export interface DistributionSchedule {
  id: string;
  name: string;
  templateId: string;
  templateName: string;
  recipients: string[];
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  dayOfWeek?: number; // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  time: string; // HH:MM format
  format: 'pdf' | 'excel' | 'pptx';
  isActive: boolean;
  lastSent?: string;
  nextScheduled: string;
}

export interface ReportWidget {
  id: string;
  type: 'chart' | 'table' | 'metric' | 'text' | 'image' | 'map';
  name: string;
  description: string;
  category: string;
  icon: string;
  defaultWidth: number; // grid units 1-12
  defaultHeight: number; // grid units
  configurable: boolean;
}

export interface ReportSettings {
  companyName: string;
  companyLogo?: string;
  primaryColor: string;
  secondaryColor: string;
  defaultFont: string;
  defaultPageSize: 'letter' | 'a4' | 'legal';
  defaultOrientation: 'portrait' | 'landscape';
  includePageNumbers: boolean;
  includeTableOfContents: boolean;
  includeTimestamp: boolean;
  footerText: string;
  headerText: string;
  watermarkText?: string;
}