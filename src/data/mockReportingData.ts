/**
 * Mock Reporting Suite Data
 * Templates, queued reports, distribution settings, and widget definitions
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

// Mock Report Templates
export const mockReportTemplates: ReportTemplate[] = [
  {
    id: 'exec-summary',
    name: 'Executive Summary',
    description: 'High-level portfolio overview with key metrics, performance highlights, and strategic insights for executive stakeholders.',
    category: 'executive',
    sections: ['Portfolio Overview', 'Key Metrics', 'Performance Highlights', 'Market Outlook', 'Strategic Recommendations'],
    lastModified: '2025-12-01',
    createdBy: 'System',
    isDefault: true,
    supportedFormats: ['pdf', 'pptx'],
    parameters: [
      { name: 'reportDate', label: 'Report Date', type: 'date', required: true, description: 'Date for the report data' },
      { name: 'includeCommentary', label: 'Include Market Commentary', type: 'boolean', required: false, defaultValue: true },
    ],
  },
  {
    id: 'financial-performance',
    name: 'Financial Performance Report',
    description: 'Comprehensive financial analysis including IRR, cash flows, NOI trends, and return metrics across the portfolio.',
    category: 'financial',
    sections: ['Income Statement', 'Cash Flow Analysis', 'Return Metrics', 'NOI Trends', 'Variance Analysis', 'Projections'],
    lastModified: '2025-11-28',
    createdBy: 'System',
    isDefault: true,
    supportedFormats: ['pdf', 'excel'],
    parameters: [
      { name: 'startDate', label: 'Start Date', type: 'date', required: true },
      { name: 'endDate', label: 'End Date', type: 'date', required: true },
      { name: 'comparePeriod', label: 'Compare to Previous Period', type: 'boolean', required: false, defaultValue: true },
      { name: 'metrics', label: 'Metrics to Include', type: 'multiselect', required: false, options: ['IRR', 'NOI', 'Cash Flow', 'Equity Multiple'] },
    ],
  },
  {
    id: 'market-analysis',
    name: 'Market Analysis Report',
    description: 'In-depth market research including rent comparables, sales comps, submarket trends, and competitive positioning.',
    category: 'market',
    sections: ['Market Overview', 'Rent Comparables', 'Sales Comparables', 'Supply Pipeline', 'Demand Drivers', 'Risk Assessment'],
    lastModified: '2025-11-25',
    createdBy: 'System',
    isDefault: true,
    supportedFormats: ['pdf', 'excel', 'pptx'],
    parameters: [
      { name: 'market', label: 'Target Market', type: 'select', required: true, options: ['Austin', 'Dallas', 'Houston', 'San Antonio', 'Denver'] },
      { name: 'radius', label: 'Comp Radius (miles)', type: 'number', required: false, defaultValue: 3 },
    ],
  },
  {
    id: 'portfolio-overview',
    name: 'Portfolio Overview',
    description: 'Complete portfolio snapshot with property details, geographic distribution, and aggregate statistics.',
    category: 'portfolio',
    sections: ['Property Summary', 'Geographic Distribution', 'Asset Allocation', 'Performance Matrix', 'Key Statistics'],
    lastModified: '2025-11-20',
    createdBy: 'System',
    isDefault: true,
    supportedFormats: ['pdf', 'excel', 'pptx'],
    parameters: [],
  },
  {
    id: 'quarterly-investor',
    name: 'Quarterly Investor Report',
    description: 'Quarterly update for LP investors with performance metrics, distributions, and market commentary.',
    category: 'executive',
    sections: ['Letter to Investors', 'Performance Summary', 'Portfolio Updates', 'Market Commentary', 'Distributions', 'Outlook'],
    lastModified: '2025-12-03',
    createdBy: 'Admin',
    isDefault: false,
    supportedFormats: ['pdf'],
    parameters: [
      { name: 'quarter', label: 'Quarter', type: 'select', required: true, options: ['Q1', 'Q2', 'Q3', 'Q4'] },
      { name: 'year', label: 'Year', type: 'number', required: true, defaultValue: 2025 },
    ],
  },
  {
    id: 'deal-memo',
    name: 'Investment Deal Memo',
    description: 'Comprehensive deal memorandum for investment committee review with financial projections and risk analysis.',
    category: 'financial',
    sections: ['Executive Summary', 'Property Overview', 'Market Analysis', 'Financial Projections', 'Risk Factors', 'Recommendation'],
    lastModified: '2025-12-02',
    createdBy: 'Admin',
    isDefault: false,
    supportedFormats: ['pdf', 'pptx'],
    parameters: [
      { name: 'dealName', label: 'Deal Name', type: 'string', required: true },
      { name: 'propertyAddress', label: 'Property Address', type: 'string', required: true },
    ],
  },
  {
    id: 'property-performance',
    name: 'Property Performance Report',
    description: 'Individual property deep-dive with operating metrics, tenant analysis, and improvement recommendations.',
    category: 'portfolio',
    sections: ['Property Details', 'Operating Performance', 'Tenant Analysis', 'CapEx Summary', 'Recommendations'],
    lastModified: '2025-11-15',
    createdBy: 'System',
    isDefault: false,
    supportedFormats: ['pdf', 'excel'],
    parameters: [
      { name: 'propertyId', label: 'Property', type: 'select', required: true, options: ['Lakewood Plaza', 'Riverside Office', 'Downtown Tower'] },
    ],
  },
  {
    id: 'sensitivity-analysis',
    name: 'Sensitivity Analysis Report',
    description: 'Multi-variable sensitivity analysis showing impact of key assumptions on returns.',
    category: 'financial',
    sections: ['Base Case', 'Exit Cap Rate Sensitivity', 'Rent Growth Scenarios', 'Interest Rate Impact', 'Combined Scenarios'],
    lastModified: '2025-11-10',
    createdBy: 'System',
    isDefault: false,
    supportedFormats: ['pdf', 'excel'],
    parameters: [],
  },
];

// Mock Queued Reports
export const mockQueuedReports: QueuedReport[] = [
  {
    id: 'queue-1',
    name: 'Q4 2025 Executive Summary',
    templateId: 'exec-summary',
    templateName: 'Executive Summary',
    status: 'completed',
    progress: 100,
    requestedBy: 'John Smith',
    requestedAt: '2025-12-05T08:30:00Z',
    completedAt: '2025-12-05T08:32:15Z',
    format: 'pdf',
    fileSize: '2.4 MB',
    downloadUrl: '/reports/q4-exec-summary.pdf',
  },
  {
    id: 'queue-2',
    name: 'November Financial Report',
    templateId: 'financial-performance',
    templateName: 'Financial Performance Report',
    status: 'generating',
    progress: 65,
    requestedBy: 'Sarah Johnson',
    requestedAt: '2025-12-05T09:15:00Z',
    format: 'excel',
  },
  {
    id: 'queue-3',
    name: 'Phoenix Market Analysis',
    templateId: 'market-analysis',
    templateName: 'Market Analysis Report',
    status: 'pending',
    progress: 0,
    requestedBy: 'Mike Chen',
    requestedAt: '2025-12-05T09:45:00Z',
    format: 'pdf',
  },
  {
    id: 'queue-4',
    name: 'Portfolio Overview - All Assets',
    templateId: 'portfolio-overview',
    templateName: 'Portfolio Overview',
    status: 'failed',
    progress: 45,
    requestedBy: 'Emily Davis',
    requestedAt: '2025-12-05T07:00:00Z',
    format: 'pptx',
    error: 'Failed to generate chart: insufficient data for property XYZ',
  },
  {
    id: 'queue-5',
    name: 'Investor Update - December',
    templateId: 'quarterly-investor',
    templateName: 'Quarterly Investor Report',
    status: 'completed',
    progress: 100,
    requestedBy: 'John Smith',
    requestedAt: '2025-12-04T14:00:00Z',
    completedAt: '2025-12-04T14:05:30Z',
    format: 'pdf',
    fileSize: '5.1 MB',
    downloadUrl: '/reports/investor-update-dec.pdf',
  },
];

// Mock Distribution Schedules
export const mockDistributionSchedules: DistributionSchedule[] = [
  {
    id: 'dist-1',
    name: 'Weekly Executive Update',
    templateId: 'exec-summary',
    templateName: 'Executive Summary',
    recipients: ['ceo@bandrcapital.com', 'cfo@bandrcapital.com', 'coo@bandrcapital.com'],
    frequency: 'weekly',
    dayOfWeek: 1, // Monday
    time: '08:00',
    format: 'pdf',
    isActive: true,
    lastSent: '2025-12-02T08:00:00Z',
    nextScheduled: '2025-12-09T08:00:00Z',
  },
  {
    id: 'dist-2',
    name: 'Monthly Financial Report',
    templateId: 'financial-performance',
    templateName: 'Financial Performance Report',
    recipients: ['finance@bandrcapital.com', 'accounting@bandrcapital.com'],
    frequency: 'monthly',
    dayOfMonth: 5,
    time: '09:00',
    format: 'excel',
    isActive: true,
    lastSent: '2025-11-05T09:00:00Z',
    nextScheduled: '2025-12-05T09:00:00Z',
  },
  {
    id: 'dist-3',
    name: 'Quarterly Investor Update',
    templateId: 'quarterly-investor',
    templateName: 'Quarterly Investor Report',
    recipients: ['investors@bandrcapital.com', 'ir@bandrcapital.com'],
    frequency: 'quarterly',
    dayOfMonth: 15,
    time: '10:00',
    format: 'pdf',
    isActive: true,
    lastSent: '2025-10-15T10:00:00Z',
    nextScheduled: '2026-01-15T10:00:00Z',
  },
  {
    id: 'dist-4',
    name: 'Daily Portfolio Summary',
    templateId: 'portfolio-overview',
    templateName: 'Portfolio Overview',
    recipients: ['asset-management@bandrcapital.com'],
    frequency: 'daily',
    time: '07:00',
    format: 'pdf',
    isActive: false,
    lastSent: '2025-11-30T07:00:00Z',
    nextScheduled: '2025-12-06T07:00:00Z',
  },
];

// Mock Report Widgets for Custom Builder
export const mockReportWidgets: ReportWidget[] = [
  // Chart Widgets
  {
    id: 'widget-line-chart',
    type: 'chart',
    name: 'Line Chart',
    description: 'Time series data visualization',
    category: 'Charts',
    icon: 'LineChart',
    defaultWidth: 6,
    defaultHeight: 3,
    configurable: true,
  },
  {
    id: 'widget-bar-chart',
    type: 'chart',
    name: 'Bar Chart',
    description: 'Categorical comparison chart',
    category: 'Charts',
    icon: 'BarChart',
    defaultWidth: 6,
    defaultHeight: 3,
    configurable: true,
  },
  {
    id: 'widget-pie-chart',
    type: 'chart',
    name: 'Pie Chart',
    description: 'Distribution visualization',
    category: 'Charts',
    icon: 'PieChart',
    defaultWidth: 4,
    defaultHeight: 3,
    configurable: true,
  },
  {
    id: 'widget-area-chart',
    type: 'chart',
    name: 'Area Chart',
    description: 'Stacked area visualization',
    category: 'Charts',
    icon: 'AreaChart',
    defaultWidth: 6,
    defaultHeight: 3,
    configurable: true,
  },
  // Table Widgets
  {
    id: 'widget-data-table',
    type: 'table',
    name: 'Data Table',
    description: 'Tabular data display',
    category: 'Tables',
    icon: 'Table',
    defaultWidth: 12,
    defaultHeight: 4,
    configurable: true,
  },
  {
    id: 'widget-summary-table',
    type: 'table',
    name: 'Summary Table',
    description: 'Condensed metrics table',
    category: 'Tables',
    icon: 'TableProperties',
    defaultWidth: 6,
    defaultHeight: 2,
    configurable: true,
  },
  // Metric Widgets
  {
    id: 'widget-kpi-card',
    type: 'metric',
    name: 'KPI Card',
    description: 'Single metric with change indicator',
    category: 'Metrics',
    icon: 'TrendingUp',
    defaultWidth: 3,
    defaultHeight: 1,
    configurable: true,
  },
  {
    id: 'widget-metric-grid',
    type: 'metric',
    name: 'Metric Grid',
    description: 'Multiple metrics in grid layout',
    category: 'Metrics',
    icon: 'LayoutGrid',
    defaultWidth: 12,
    defaultHeight: 2,
    configurable: true,
  },
  {
    id: 'widget-gauge',
    type: 'metric',
    name: 'Gauge Chart',
    description: 'Progress or threshold indicator',
    category: 'Metrics',
    icon: 'Gauge',
    defaultWidth: 3,
    defaultHeight: 2,
    configurable: true,
  },
  // Text Widgets
  {
    id: 'widget-text-block',
    type: 'text',
    name: 'Text Block',
    description: 'Rich text content area',
    category: 'Content',
    icon: 'FileText',
    defaultWidth: 12,
    defaultHeight: 2,
    configurable: true,
  },
  {
    id: 'widget-heading',
    type: 'text',
    name: 'Section Heading',
    description: 'Section title with optional subtitle',
    category: 'Content',
    icon: 'Heading',
    defaultWidth: 12,
    defaultHeight: 1,
    configurable: true,
  },
  // Image Widgets
  {
    id: 'widget-image',
    type: 'image',
    name: 'Image',
    description: 'Static image or logo',
    category: 'Content',
    icon: 'Image',
    defaultWidth: 4,
    defaultHeight: 2,
    configurable: true,
  },
  // Map Widgets
  {
    id: 'widget-property-map',
    type: 'map',
    name: 'Property Map',
    description: 'Geographic property visualization',
    category: 'Maps',
    icon: 'Map',
    defaultWidth: 6,
    defaultHeight: 4,
    configurable: true,
  },
  {
    id: 'widget-heat-map',
    type: 'map',
    name: 'Heat Map',
    description: 'Geographic data density map',
    category: 'Maps',
    icon: 'MapPin',
    defaultWidth: 6,
    defaultHeight: 4,
    configurable: true,
  },
];

// Helper function to get template by category
export function getTemplatesByCategory(category: ReportTemplate['category']): ReportTemplate[] {
  return mockReportTemplates.filter(t => t.category === category);
}

// Helper function to get widgets by type
export function getWidgetsByType(type: ReportWidget['type']): ReportWidget[] {
  return mockReportWidgets.filter(w => w.type === type);
}

// Helper function to get active schedules
export function getActiveSchedules(): DistributionSchedule[] {
  return mockDistributionSchedules.filter(s => s.isActive);
}
