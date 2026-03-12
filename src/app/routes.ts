import { lazy } from 'react';

// All pages are lazy-loaded for code splitting.
// DashboardMain is lazy too — the Suspense fallback provides instant feedback
// while the dashboard chunk loads (typically from cache on repeat visits).
export const DashboardMain = lazy(() =>
  import('@/features/dashboard-main/DashboardMain').then(m => ({ default: m.DashboardMain }))
);
export const AnalyticsPage = lazy(() =>
  import('@/features/analytics').then(m => ({ default: m.AnalyticsPage }))
);
export const InvestmentsPage = lazy(() =>
  import('@/features/investments').then(m => ({ default: m.InvestmentsPage }))
);
export const PropertyDetailPage = lazy(() =>
  import('@/features/property-detail').then(m => ({ default: m.PropertyDetailPage }))
);
export const MappingPage = lazy(() =>
  import('@/features/mapping').then(m => ({ default: m.MappingPage }))
);
export const DealsPage = lazy(() =>
  import('@/features/deals').then(m => ({ default: m.DealsPage }))
);
export const MarketPage = lazy(() =>
  import('@/features/market').then(m => ({ default: m.MarketPage }))
);
export const USAMarketPage = lazy(() =>
  import('@/features/market').then(m => ({ default: m.USAMarketPage }))
);
export const DocumentsPage = lazy(() =>
  import('@/features/documents').then(m => ({ default: m.DocumentsPage }))
);
export const InterestRatesPage = lazy(() =>
  import('@/features/interest-rates').then(m => ({ default: m.InterestRatesPage }))
);
export const ReportingSuitePage = lazy(() =>
  import('@/features/reporting-suite').then(m => ({ default: m.ReportingSuitePage }))
);
export const ExtractionDashboard = lazy(() =>
  import('@/features/extraction').then(m => ({ default: m.ExtractionDashboard }))
);
export const DealComparisonPage = lazy(() =>
  import('@/features/deals/DealComparisonPage').then(m => ({ default: m.DealComparisonPage }))
);
export const SalesAnalysisPage = lazy(() =>
  import('@/features/sales-analysis').then(m => ({ default: m.SalesAnalysisPage }))
);
export const ConstructionPipelinePage = lazy(() =>
  import('@/features/construction-pipeline').then(m => ({ default: m.ConstructionPipelinePage }))
);
export const TransactionsPage = lazy(() =>
  import('@/features/transactions').then(m => ({ default: m.TransactionsPage }))
);

// Router configuration options
export const routerOptions = {
  future: {
    v7_relativeSplatPath: true,
  },
};

// Route path constants for type-safe navigation
export const LoginPage = lazy(() =>
  import('@/features/auth').then(m => ({ default: m.LoginPage }))
);

export const ROUTES = {
  LOGIN: '/login',
  HOME: '/',
  INVESTMENTS: '/investments',
  PROPERTY_DETAIL: '/properties/:id',
  DEALS: '/deals',
  DEALS_COMPARE: '/deals/compare',
  ANALYTICS: '/analytics',
  MAPPING: '/mapping',
  MARKET: '/market',
  MARKET_USA: '/market/usa',
  DOCUMENTS: '/documents',
  INTEREST_RATES: '/interest-rates',
  REPORTING: '/reporting',
  EXTRACTION: '/extraction',
  EXTRACTION_PROPERTY: '/extraction/:propertyName',
  SALES_ANALYSIS: '/sales-analysis',
  CONSTRUCTION_PIPELINE: '/construction-pipeline',
  TRANSACTIONS: '/transactions',
} as const;

export type RoutePath = typeof ROUTES[keyof typeof ROUTES];
