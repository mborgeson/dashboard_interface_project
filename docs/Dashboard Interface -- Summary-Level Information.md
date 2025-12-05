# B&R Capital Real Estate Analytics Dashboard - Production Build

## Executive Summary
Build a production-ready real estate investment analytics platform for B&R Capital, a multifamily-focused PE firm in Phoenix MSA. Desktop-first design (mobile version in future phase). Dashboard tracks portfolio performance, property-level financials, market analytics, and deal underwriting across 12 Phoenix properties, structured for PostgreSQL integration with 50,000+ data points.

## Project Initialization

### Tech Stack
```bash
# Core Framework
- React 18.3+ with TypeScript 5.5+ (strict mode, no 'any' types)
- Vite 6.0+ for build tooling  
- React Router v6.28+ for routing
- TailwindCSS 3.4+ for styling

# UI Components & Design
- shadcn/ui component library
- Lucide React for icons (consistent icon set)
- Radix UI primitives (Accordion, Tooltip, Select, Dialog)
- Headless UI for advanced interactions

# Data Visualization
- Recharts 2.13+ (primary - responsive, React-native)
- Chart.js 4.5+ with react-chartjs-2 (for tornado/sensitivity charts)
- React Leaflet 4.2+ for mapping
- Leaflet 1.9+ base library
- Leaflet.markercluster 1.5+ for property clustering

# State Management & Data Fetching
- Zustand 5.0+ for global state (lightweight, no boilerplate)
- React Query 5.59+ (@tanstack/react-query) for server state
- Axios 1.7+ for HTTP client with interceptors

# Tables & Forms
- TanStack Table v8 (@tanstack/react-table) for advanced tables
- React Hook Form 7.54+ for performant forms
- Zod 3.24+ for runtime type validation

# Utilities
- date-fns 4.1+ for date manipulation (lighter than moment)
- clsx + tailwind-merge for dynamic className composition
- jsPDF 2.5+ for PDF generation
- xlsx 0.18+ (SheetJS) for Excel export
- fuse.js 7.0+ for fuzzy search in global search bar
```

### Installation Commands
```bash
# Initialize project
npm create vite@latest dashboard_interface_project -- --template react-ts
cd dashboard_interface_project

# Core dependencies
npm install react-router-dom@6 zustand@5 @tanstack/react-query@5 axios

# Visualization libraries
npm install recharts@2 chart.js@4 react-chartjs-2
npm install react-leaflet@4 leaflet@1.9 leaflet.markercluster@1.5

# Tables and forms
npm install @tanstack/react-table@8 react-hook-form@7 @hookform/resolvers zod

# Utilities
npm install date-fns clsx tailwind-merge lucide-react fuse.js
npm install jspdf xlsx

# Tailwind CSS
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p

# shadcn/ui setup
npx shadcn@latest init
# When prompted: Style: Default, Base color: Neutral, CSS variables: Yes

# Install shadcn components
npx shadcn@latest add button card dialog dropdown-menu table tabs
npx shadcn@latest add select accordion tooltip badge input label
npx shadcn@latest add skeleton alert-dialog separator

# Type definitions
npm install -D @types/leaflet @types/leaflet.markercluster
npm install -D eslint@8 prettier eslint-config-prettier
npm install -D @typescript-eslint/eslint-plugin @typescript-eslint/parser
```

### Project Structure
```
dashboard_interface_project/
├── public/
│   └── property-images/          # Broker package photos
│       ├── arcadia-heights/
│       │   ├── main.jpg
│       │   ├── amenities-01.jpg
│       │   └── floorplan-2br.jpg
│       └── [property-name]/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   └── layout/
│   │       ├── AppLayout.tsx
│   │       ├── Sidebar.tsx
│   │       ├── TopNav.tsx
│   │       └── GlobalSearch.tsx
│   ├── features/
│   │   ├── dashboard-main/
│   │   │   ├── DashboardMain.tsx
│   │   │   ├── components/
│   │   │   │   ├── HeroStats.tsx
│   │   │   │   ├── PortfolioPerformanceChart.tsx
│   │   │   │   ├── PropertyDistributionChart.tsx
│   │   │   │   ├── TopPerformingTable.tsx
│   │   │   │   ├── RecentTransactions.tsx
│   │   │   │   └── PropertyMap.tsx
│   │   │   └── hooks/
│   │   │       ├── usePortfolioStats.ts
│   │   │       └── useTimeSeriesData.ts
│   │   ├── investments/
│   │   ├── analytics/
│   │   ├── mapping/
│   │   ├── reports/
│   │   ├── economic-data/
│   │   └── underwriting/
│   │       ├── UnderwritingCalculator.tsx
│   │       ├── components/
│   │       │   ├── InputForm.tsx
│   │       │   ├── ResultsPanel.tsx
│   │       │   ├── CashFlowTable.tsx
│   │       │   ├── SensitivityChart.tsx
│   │       │   └── EquityBuildupChart.tsx
│   │       ├── hooks/
│   │       │   └── useUnderwritingCalculations.ts
│   │       └── calculations.ts
│   ├── components/
│   │   ├── ui/                   # shadcn components
│   │   ├── charts/
│   │   │   ├── SparklineChart.tsx
│   │   │   ├── TornadoChart.tsx
│   │   │   └── CustomTooltip.tsx
│   │   └── common/
│   │       ├── StatCard.tsx
│   │       ├── PageHeader.tsx
│   │       ├── EmptyState.tsx
│   │       └── LoadingSkeleton.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts         # Axios instance with interceptors
│   │   │   ├── properties.ts
│   │   │   ├── transactions.ts
│   │   │   └── market-data.ts
│   │   ├── calculations/
│   │   │   ├── irr.ts            # Newton-Raphson IRR
│   │   │   ├── npv.ts
│   │   │   ├── cashflow.ts       # 10-year projections
│   │   │   ├── returns.ts        # Cash-on-cash, equity multiple
│   │   │   └── sensitivity.ts    # Tornado chart calculations
│   │   └── utils/
│   │       ├── formatters.ts     # Currency, percent, number
│   │       ├── validators.ts     # Zod schemas
│   │       └── exports.ts        # PDF/Excel generation
│   ├── hooks/
│   │   ├── useProperties.ts
│   │   ├── useTransactions.ts
│   │   ├── useMarketData.ts
│   │   ├── useFilters.ts
│   │   ├── useExport.ts
│   │   └── useGlobalSearch.ts
│   ├── store/
│   │   ├── useAppStore.ts        # Global UI state
│   │   ├── useFilterStore.ts     # Filter persistence
│   │   └── useUserStore.ts       # User preferences
│   ├── types/
│   │   ├── property.ts
│   │   ├── transaction.ts
│   │   ├── market.ts
│   │   ├── underwriting.ts
│   │   └── index.ts              # Re-export all types
│   ├── data/
│   │   ├── mockProperties.ts     # 12 Phoenix properties
│   │   ├── mockTransactions.ts   # 100+ transactions
│   │   ├── mockMarketData.ts     # Historical market data
│   │   └── generators.ts         # Data generation utilities
│   ├── styles/
│   │   └── globals.css
│   ├── main.tsx
│   └── vite-env.d.ts
├── .env.example
├── .eslintrc.cjs
├── .prettierrc
├── .gitignore
├── components.json              # shadcn config
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Design System (Gentelella-Inspired)

### Color Palette (tailwind.config.js)
```javascript
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#2A3F54',  // Main brand - dark blue
          600: '#243644',
          700: '#1e2d3a',
          800: '#182430',
          900: '#121b26',
        },
        accent: {
          50: '#fee2e2',
          100: '#fecaca',
          500: '#E74C3C',  // Active state red
          600: '#c0392b',
          700: '#a93226',
        },
        neutral: {
          50: '#f9fafb',
          100: '#f3f4f6',   // Card background alternate
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',   // Sidebar background
          900: '#111827',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'hero-stat': ['2.5rem', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '-0.02em' }],
        'page-title': ['1.875rem', { lineHeight: '2.25rem', fontWeight: '600' }],
        'section-title': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'card-title': ['1.125rem', { lineHeight: '1.75rem', fontWeight: '600' }],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
```

### Layout Specifications
- **Sidebar:** 260px expanded, 70px collapsed, `bg-neutral-800`, fixed position
- **Top Nav:** 60px height, `bg-neutral-800`, fixed, z-index 40
- **Main Content:** 
  - Margin-left: 260px (sidebar expanded) or 70px (collapsed)
  - Margin-top: 60px (top nav)
  - Padding: 24px
  - Max-width: 1920px
  - Background: white
- **Cards:** 
  - Background: white
  - Border-radius: 8px
  - Padding: 24px
  - Shadow: `shadow-card`
  - Hover: `shadow-card-hover` with `transition-shadow duration-200`
- **Grid Gaps:** 24px (6 in Tailwind)
- **Section Spacing:** 32px between major sections

### Typography Scale
```css
/* Page Title */
.page-title { @apply text-page-title text-neutral-900 font-semibold mb-6; }

/* Section Title */
.section-title { @apply text-section-title text-neutral-800 font-semibold mb-4; }

/* Card Title */
.card-title { @apply text-card-title text-neutral-800 font-semibold; }

/* Body Text */
.body { @apply text-base text-neutral-700; }

/* Small Text */
.text-small { @apply text-sm text-neutral-600; }

/* Stat Value */
.stat-value { @apply text-hero-stat text-neutral-900; }
```

## TypeScript Interfaces

### src/types/property.ts
```typescript
export interface Property {
  id: string;
  name: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    latitude: number;
    longitude: number;
    submarket: PhoenixSubmarket;
  };
  propertyDetails: {
    units: number;
    squareFeet: number;
    averageUnitSize: number;
    yearBuilt: number;
    propertyClass: 'A' | 'B' | 'C';
    assetType: 'Garden' | 'Mid-Rise' | 'High-Rise';
    amenities: string[];
  };
  acquisition: {
    date: Date;
    purchasePrice: number;
    pricePerUnit: number;
    closingCosts: number;
    acquisitionFee: number;
    totalInvested: number;
  };
  financing: {
    loanAmount: number;
    loanToValue: number;
    interestRate: number;
    loanTerm: number;
    amortization: number;
    monthlyPayment: number;
    lender: string;
    originationDate: Date;
    maturityDate: Date;
  };
  valuation: {
    currentValue: number;
    lastAppraisalDate: Date;
    capRate: number;
    appreciationSinceAcquisition: number;
  };
  operations: {
    occupancy: number;
    averageRent: number;
    rentPerSqft: number;
    monthlyRevenue: number;
    otherIncome: number;
    monthlyExpenses: {
      propertyTax: number;
      insurance: number;
      utilities: number;
      management: number;
      repairs: number;
      payroll: number;
      marketing: number;
      other: number;
      total: number;
    };
    noi: number;
    operatingExpenseRatio: number;
  };
  performance: {
    cashOnCashReturn: number;
    irr: number;
    equityMultiple: number;
    totalReturnDollars: number;
    totalReturnPercent: number;
  };
  images: {
    main: string;
    gallery: string[];
  };
}

export type PhoenixSubmarket = 
  | 'Scottsdale' 
  | 'Tempe' 
  | 'Mesa' 
  | 'Gilbert' 
  | 'Chandler' 
  | 'Phoenix Central' 
  | 'Phoenix North' 
  | 'Phoenix West';

export interface PropertySummaryStats {
  totalProperties: number;
  totalUnits: number;
  totalValue: number;
  totalInvested: number;
  totalNOI: number;
  averageOccupancy: number;
  averageCapRate: number;
  portfolioCashOnCash: number;
  portfolioIRR: number;
}
```

### src/types/transaction.ts
```typescript
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
```

### src/types/market.ts
```typescript
export interface MarketData {
  id: string;
  submarket: string;
  date: Date;
  metrics: {
    totalUnits: number;
    vacancy: number;
    averageRent: number;
    rentGrowthYoY: number;
    capRateRange: [number, number];
    newSupply: number;
    absorption: number;
  };
}

export interface EconomicIndicator {
  id: string;
  indicator: 'population' | 'employment' | 'income' | 'permits';
  date: Date;
  value: number;
  change: number;
  region: 'Phoenix MSA' | 'Arizona' | 'United States';
}
```

### src/types/underwriting.ts
```typescript
export interface UnderwritingInputs {
  // Property Information
  propertyName: string;
  address: string;
  units: number;
  squareFeet: number;
  yearBuilt: number;
  
  // Financial Assumptions
  purchasePrice: number;
  downPaymentPercent: number;
  interestRate: number;
  loanTerm: number;
  closingCostsPercent: number;
  
  // Income Projections
  currentRentPerUnit: number;
  rentGrowthPercent: number;
  otherIncomePerUnit: number;
  otherIncomeGrowthPercent: number;
  vacancyPercent: number;
  
  // Operating Expenses (per unit per year)
  propertyTaxPerUnit: number;
  insurancePerUnit: number;
  utilitiesPerUnit: number;
  managementPercent: number;
  repairsPercent: number;
  payrollPerUnit: number;
  capexReservePercent: number;
  
  // Exit Assumptions
  holdPeriod: number;
  exitCapRate: number;
  sellingCostsPercent: number;
}

export interface UnderwritingResults {
  // Acquisition Metrics
  downPayment: number;
  loanAmount: number;
  closingCosts: number;
  totalEquityRequired: number;
  
  // Year 1 Metrics
  year1: {
    grossIncome: number;
    vacancy: number;
    effectiveGrossIncome: number;
    operatingExpenses: number;
    noi: number;
    debtService: number;
    cashFlow: number;
    cashOnCashReturn: number;
    debtServiceCoverageRatio: number;
  };
  
  // 10-Year Projections
  cashFlowProjection: YearlyProjection[];
  
  // Return Metrics
  leveredIRR: number;
  unleveredIRR: number;
  equityMultiple: number;
  averageAnnualReturn: number;
  totalProfit: number;
  
  // Exit Analysis
  exitValue: number;
  loanPaydown: number;
  saleProceeds: number;
}

export interface YearlyProjection {
  year: number;
  grossIncome: number;
  vacancy: number;
  effectiveGrossIncome: number;
  operatingExpenses: number;
  noi: number;
  debtService: number;
  cashFlow: number;
  cumulativeCashFlow: number;
  propertyValue: number;
  loanBalance: number;
  equity: number;
}

export interface SensitivityVariable {
  name: string;
  label: string;
  baseValue: number;
  lowValue: number;
  highValue: number;
  lowIRR: number;
  highIRR: number;
  impact: number;
}
```

## Mock Data Requirements

### Phoenix MSA Properties (src/data/mockProperties.ts)

Create **12 properties** with realistic Phoenix MSA data:

**Distribution:**
- **Submarkets:** Scottsdale (2), Tempe (2), Mesa (2), Gilbert (2), Chandler (2), Phoenix Central (2)
- **Classes:** 4 Class A, 5 Class B, 3 Class C
- **Unit Counts:** 50-320 units
- **Acquisition Dates:** 2019-2024

**Property Classes & Financials:**

**Class A (4 properties):**
- Units: 150-280
- Year Built: 2012-2020
- Rent/Unit: $1,800-$2,500
- Cap Rate: 4.5%-5.5%
- Occupancy: 93%-97%
- Purchase: 2020-2023

**Class B (5 properties):**
- Units: 80-200
- Year Built: 1995-2011
- Rent/Unit: $1,400-$1,800
- Cap Rate: 5.0%-6.0%
- Occupancy: 90%-95%
- Purchase: 2019-2022

**Class C (3 properties):**
- Units: 50-120
- Year Built: 1980-1994
- Rent/Unit: $1,100-$1,400
- Cap Rate: 5.5%-6.5%
- Occupancy: 85%-92%
- Purchase: 2019-2021

**Example Property Structure:**
```typescript
{
  id: 'prop-001',
  name: 'Arcadia Heights',
  address: {
    street: '4500 N Scottsdale Rd',
    city: 'Scottsdale',
    state: 'AZ',
    zip: '85251',
    latitude: 33.4952,
    longitude: -111.9260,
    submarket: 'Scottsdale',
  },
  propertyDetails: {
    units: 180,
    squareFeet: 180000,
    averageUnitSize: 1000,
    yearBuilt: 2015,
    propertyClass: 'A',
    assetType: 'Garden',
    amenities: ['Pool', 'Fitness Center', 'Business Center', 'Dog Park', 'EV Charging'],
  },
  // ... complete all fields with realistic Phoenix market data
}
```

Use actual Phoenix MSA coordinates from Google Maps for each submarket. Include realistic amenities, financing terms, and performance metrics based on current Phoenix multifamily market conditions.

### Transactions (src/data/mockTransactions.ts)

Generate **100+ transactions** with this distribution:
- **Acquisitions:** 12 (one per property)
- **Capital Improvements:** 30-40 (renovations, capex projects)
- **Refinances:** 3-5 (selective properties)
- **Distributions:** 40-50 (quarterly distributions to investors)

## Phase 1: Core Implementation

### Priority Order
1. **Project Setup** - Initialize Vite project, install all dependencies, configure Tailwind/TypeScript
2. **TypeScript Interfaces** - Define all data types (property, transaction, market, underwriting)
3. **Mock Data** - Generate 12 realistic Phoenix properties + 100+ transactions
4. **Layout System** - Build AppLayout, Sidebar (collapsible), TopNav with global search
5. **Dashboard Main Page** - Hero stats, performance chart, distribution chart, property map, recent transactions
6. **Underwriting Calculator** - Complete modal with input form, results panel, 10-year projection, sensitivity analysis

### Key Features to Implement

#### 1. Collapsible Sidebar
- Width: 260px expanded, 70px collapsed
- Dark background (#1F2937)
- Icons with tooltips when collapsed
- Active state: red accent color (#E74C3C)
- Smooth transition (300ms)
- Organized sections: Dashboard, B&R Websites, B&R Tools

#### 2. Global Search (Real-Time)
- Fuzzy search using Fuse.js
- Search across properties and transactions
- Dropdown results as you type
- Categorized results (Properties, Transactions)
- Keyboard navigation (↑↓ arrows, Enter to select)
- Click result to navigate to detail view

#### 3. Dashboard Main Components

**Hero Stats (4 cards):**
- Portfolio Value (with % change badge, sparkline)
- Total Units (with occupancy % subtitle)
- Monthly NOI (with YoY comparison, sparkline)
- Average Cap Rate (vs market benchmark)

**Portfolio Performance Chart:**
- Line chart showing 12-month trend
- Multiple series: Portfolio Value, NOI, Cash Flow
- Time selector buttons: 1M, 3M, 6M (default), 1Y, ALL
- Custom tooltip with detailed breakdowns
- Responsive (Recharts)

**Property Distribution Chart:**
- Interactive pie/doughnut chart
- Toggle between: Asset Class, Location, Acquisition Year
- Click segment to filter/drill down
- Legend with values and percentages

**Property Map (Leaflet):**
- Full interactive map centered on Phoenix (33.4484, -112.0740)
- Property markers with clustering (active below zoom level 12)
- Color-coded by performance: Green (>8% CoC), Yellow (6-8%), Red (<6%)
- Marker size represents unit count
- Click marker for popup with:
  - Property name
  - Address
  - Key metrics (units, occupancy, rent/unit)
  - "View Details" button
- Map controls: zoom, pan, layer toggle (street/satellite)

#### 4. Property Underwriting Calculator

**Modal Dialog (accessible via top nav button + keyboard shortcut Ctrl+U):**

**Layout:**
- Left panel (40%): Input form (scrollable)
- Right panel (40%): Results (sticky)
- Bottom section (20%): 10-year cash flow table

**Input Sections:**
1. Property Information (name, address, units, sqft, year built)
2. Financial Assumptions (purchase price, down payment %, interest rate, loan term, closing costs %)
3. Income Projections (rent/unit, rent growth %, other income/unit, vacancy %)
4. Operating Expenses (property tax, insurance, utilities, management %, repairs %, payroll, capex %)
5. Exit Assumptions (hold period, exit cap rate, selling costs %)

**Results Panel:**
- Year 1 Metrics Cards (NOI, Cash-on-Cash, DSCR)
- Returns Summary Cards (Levered IRR, Unlevered IRR, Equity Multiple, Avg Annual Return)
- Charts:
  - Cash flow waterfall (Recharts)
  - Equity buildup area chart
  - **Sensitivity Analysis Tornado Chart** (Chart.js)

**Sensitivity Analysis (6 Variables):**
Analyze IRR impact of ±10% change in:
1. Exit cap rate (±0.5%)
2. Rent growth % (±1%)
3. Exit period/Hold period (±2 years)
4. Total income per unit per year (±10%)
5. Total operating expenses per unit per year (±10%)
6. Senior loan interest rate (±0.5%)

Display as horizontal bar chart (tornado), sorted by absolute impact (largest at top).

**10-Year Projection Table:**
Columns: Year, Gross Income, Vacancy, Effective Gross Income, Operating Expenses, NOI, Debt Service, Cash Flow, Cumulative Cash Flow
- Scrollable
- Export to Excel button
- Highlight Year 1 and Exit Year

**Actions:**
- Save Model button (saves to mock localStorage)
- Export to PDF (jsPDF)
- Reset Form button
- Compare to Portfolio Average button

### Utility Functions

#### src/lib/calculations/irr.ts
Implement Newton-Raphson method for IRR calculation:
```typescript
export function calculateIRR(cashFlows: number[]): number {
  let guess = 0.1;
  const maxIterations = 100;
  const tolerance = 0.0001;
  
  for (let i = 0; i < maxIterations; i++) {
    let npv = 0;
    let dnpv = 0;
    
    for (let t = 0; t < cashFlows.length; t++) {
      npv += cashFlows[t] / Math.pow(1 + guess, t);
      dnpv -= t * cashFlows[t] / Math.pow(1 + guess, t + 1);
    }
    
    const newGuess = guess - npv / dnpv;
    
    if (Math.abs(newGuess - guess) < tolerance) {
      return newGuess;
    }
    
    guess = newGuess;
  }
  
  return guess;
}
```

#### src/lib/calculations/sensitivity.ts
Calculate sensitivity analysis for tornado chart:
```typescript
export function calculateSensitivity(
  baseInputs: UnderwritingInputs,
  baseResults: UnderwritingResults
): SensitivityVariable[] {
  const variables: SensitivityVariable[] = [
    {
      name: 'exitCapRate',
      label: 'Exit Cap Rate',
      baseValue: baseInputs.exitCapRate,
      lowValue: baseInputs.exitCapRate - 0.005,
      highValue: baseInputs.exitCapRate + 0.005,
    },
    // ... define all 6 variables
  ];
  
  // For each variable, calculate IRR with low and high values
  // Sort by absolute impact
  // Return sorted array
}
```

#### src/lib/utils/formatters.ts
```typescript
export function formatCurrency(value: number, compact = false): string {
  if (compact && value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}
```

## Code Quality Standards

**TypeScript:**
- Strict mode enabled (no `any` types)
- Explicit return types on functions
- Interface > Type (except for unions)
- Use `unknown` instead of `any` when type is truly unknown

**React:**
- Functional components only (no class components)
- Custom hooks for reusable logic (prefix with `use`)
- Memoize expensive calculations with `useMemo`
- Debounce search inputs (300ms)
- Error boundaries around major features

**Performance:**
- Lazy load routes: `const Analytics = lazy(() => import('./features/analytics'))`
- Code split by route (Vite does this automatically)
- Virtual scrolling for tables >100 rows (if needed later)
- Optimize Leaflet map (only render when Mapping page is active)

**Naming Conventions:**
- PascalCase: Components, Types, Interfaces
- camelCase: functions, variables, hooks
- SCREAMING_SNAKE_CASE: constants
- kebab-case: file names

**Error Handling:**
- Try-catch around async operations
- Error boundaries for component tree errors
- User-friendly error messages (no stack traces in UI)
- Fallback UI for failed components

## Implementation Instructions

**Start with complete project setup:**
1. Initialize Vite React TypeScript project
2. Install ALL dependencies listed above
3. Configure Tailwind with custom design system
4. Set up shadcn/ui
5. Configure ESLint and Prettier
6. Initialize Git repository

**Then build in this order:**
1. TypeScript interfaces (types folder)
2. Mock data generators (data folder)
3. Layout components (Sidebar, TopNav, AppLayout)
4. Routing setup (React Router)
5. Dashboard Main page (all components)
6. Underwriting Calculator (complete modal)
7. Utility functions (calculations, formatters)
8. React Query setup
9. Zustand stores
10. Polish (loading states, error handling, animations)

**For each component:**
- Define TypeScript interfaces/props first
- Implement core functionality
- Add loading skeletons
- Add error states
- Style with Tailwind (follow design system)
- Add hover effects and transitions
- Test with mock data

## Success Criteria

After Phase 1 completion:
✅ Dashboard loads in < 2 seconds
✅ No TypeScript errors (npm run build succeeds)
✅ All 12 mock properties display correctly
✅ Sidebar collapses/expands smoothly (300ms transition)
✅ Global search returns results in real-time
✅ Map renders with property markers and clustering
✅ Performance chart shows 6-month data by default
✅ Underwriting calculator calculates accurate IRR
✅ Sensitivity analysis shows 6 variables correctly
✅ 10-year projection table displays all years
✅ PDF export works
✅ No console errors or warnings
✅ Responsive on desktop (1280px - 1920px)

## Phase 2 Preview

Once Phase 1 is complete and tested, Phase 2 will add:
- **Investments Page:** Detailed property table with drill-down, P&L statements
- **Analytics Page:** Comparative analysis, market comps, financial ratios
- **Mapping Page:** Enhanced mapping with submarket analysis, drive-time polygons

## Questions to Resolve During Build

If you encounter any of these situations, pause and ask me:
1. Should property images use placeholder service (e.g., placeholder.com) or leave paths empty?
2. For the sensitivity chart, should I show all 6 variables even if some have minimal impact, or only show top 5?
3. Should the global search also search through report names and documents, or just properties and transactions for now?
4. For map clustering, should clicking a cluster zoom in or show a list of properties in that cluster?
5. Should I add a "Quick Actions" widget to Dashboard Main (e.g., "Add Property", "Generate Report")?

## Build Command Reminder

When you're ready to test:
```bash
npm run dev
```

Then open http://localhost:5173 in your browser.

To build for production:
```bash
npm run build
```

## Final Notes

- Use descriptive commit messages (e.g., "feat: add underwriting calculator with sensitivity analysis")
- Comment complex financial calculations
- Add JSDoc comments to utility functions
- Keep components under 300 lines (split if larger)
- DRY principle: extract repeated logic into hooks or utilities
- Accessibility: keyboard navigation, ARIA labels, focus management

I wanted to note that I have already synced the remote GitHub repository with a folder on my computer and the path is "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project".

**Ready to build Phase 1. Begin with project initialization and work sequentially through all components.**