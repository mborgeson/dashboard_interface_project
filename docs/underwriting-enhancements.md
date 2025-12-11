# Underwriting Section Enhancements

## Overview
Enhanced the B&R Capital Real Estate Analytics Dashboard underwriting feature with comprehensive inputs, assumptions, and professional-grade calculations.

## What Was Enhanced

### 1. New Input Sections (InputsTab.tsx)

#### Property Assumptions
- Property Class selector (A/B/C)
- Asset Type (Garden, Mid-Rise, High-Rise)
- Year Built
- Number of Units
- Average Unit Size (SF)
- Market/Submarket selection

#### Acquisition Assumptions
- Purchase Price with calculated Price/Unit and Price/SF
- Closing Costs (% of purchase)
- Acquisition Fee (%)
- Due Diligence Costs
- Immediate CapEx Reserve
- Real-time calculation displays

#### Financing Assumptions
- Loan Type dropdown (Agency, CMBS, Bridge, Bank)
- LTV slider (50-85%)
- Interest Rate slider
- Loan Term
- Amortization Period
- Interest-Only Period
- Origination Fee (%)
- Prepayment Penalty Type selector

#### Revenue Assumptions
- Current In-Place Rent ($/unit/month)
- Market Rent ($/unit/month)
- Rent Growth Rate (annual %)
- Other Income ($/unit/month)
- Vacancy Rate slider (%)
- Concessions slider (%)
- Bad Debt slider (%)

#### Operating Expense Assumptions
- Property Taxes ($/unit/year)
- Insurance ($/unit/year)
- Utilities ($/unit/year)
- Management Fee (% of EGI)
- Repairs & Maintenance ($/unit/year)
- Payroll ($/unit/year)
- Marketing ($/unit/year)
- Other Expenses ($/unit/year)
- Expense Growth Rate (%)
- Capital Reserve ($/unit/year)

#### Exit Assumptions
- Hold Period slider (3-10 years)
- Exit Cap Rate slider
- Disposition Fee (%)
- Cap Rate Spread (compression/expansion from entry)

### 2. Assumptions Presets Component (AssumptionsPresets.tsx)

#### Built-in Presets
- **Conservative**: Higher reserves, lower leverage, cap rate expansion
- **Moderate**: Balanced assumptions for stabilized assets
- **Aggressive**: Optimistic growth, higher leverage, cap compression

#### Custom Preset Management
- Save current inputs as custom preset (localStorage)
- Load previously saved custom presets
- Export presets to JSON file
- Import presets from JSON file
- Preset indicator showing current LTV, Vacancy, Exit Cap

### 3. Enhanced Calculation Utilities (utils/calculations.ts)

New calculation functions:
- `calculateDebtService()` - Monthly payment with IO period support
- `calculateDSCR()` - Debt Service Coverage Ratio
- `calculateLTV()` - Loan-to-Value ratio
- `calculateYieldOnCost()` - NOI / Total Basis
- `calculateIRR()` - Internal Rate of Return (Newton-Raphson)
- `calculateEquityMultiple()` - Total return / Initial equity
- `calculateLoanBalance()` - Balance with IO period support
- `calculateBreakEvenOccupancy()` - Cash break-even point
- `calculateEffectiveRent()` - After concessions
- `calculatePricePerUnit()` - Purchase price / units
- `calculatePricePerSF()` - Purchase price / SF

### 4. Enhanced Results Display (ResultsTab.tsx)

#### New Metrics Displayed
- **Investment Summary Box**: Purchase price, total equity, IRR at-a-glance
- **Acquisition Metrics**: Price/unit, Price/SF, LTV, closing & fees breakdown
- **Loan Details Section**: Loan amount, LTV, annual debt service, DSCR
- **Year 1 Performance Ratios**:
  - Cash-on-Cash Return
  - DSCR
  - Yield on Cost
  - Cash Break-Even Occupancy
- **Enhanced Exit Analysis**: Includes disposition fee

### 5. Updated Type Definitions (types/underwriting.ts)

New types:
- `PropertyClass`: 'A' | 'B' | 'C'
- `AssetType`: 'Garden' | 'Mid-Rise' | 'High-Rise'
- `LoanType`: 'Agency' | 'CMBS' | 'Bridge' | 'Bank'
- `PrepaymentPenaltyType`: 'Yield Maintenance' | 'Defeasance' | 'Step-Down' | 'None'
- `AssumptionPreset`: Preset configuration interface

Enhanced interfaces:
- `UnderwritingInputs`: 40+ fields covering all aspects
- `UnderwritingResults`: Additional calculated metrics
- `YearlyProjection`: Added concessions, bad debt fields

### 6. Enhanced Hook Logic (useUnderwriting.ts)

Updates:
- Support for all new input fields
- Comprehensive equity requirement calculation
- LTV-based loan amount calculation
- Interest-only period support
- Concessions and bad debt in revenue waterfall
- Granular expense tracking by category
- Exit cap rate spread application

### 7. Updated Cashflow Projections (cashflow.ts)

Enhancements:
- Support for interest-only periods
- Concessions and bad debt projections
- Expense growth by category
- Capital reserve tracking
- Exit cap rate with spread adjustment

### 8. Enhanced Sensitivity Analysis (sensitivity.ts)

New sensitivity variables:
- Exit Cap Rate (±0.5%)
- Rent Growth (±1%)
- Hold Period (±2 years)
- Current Rent (±10%)
- Vacancy Rate (±2%)
- Interest Rate (±0.5%)
- Property Tax (±10%)
- Expense Growth (±1%)

## UI/UX Improvements

### Collapsible Sections
- All input groups are collapsible for better organization
- Default open for easy access
- Clean expand/collapse animations

### Input Types
- **Sliders**: For percentages with visual min/max indicators
- **Number inputs**: For currency and counts
- **Dropdowns**: For categorical selections
- **Tooltips**: Help icons with explanations for complex terms

### Layout
- Responsive 2-column grid layout
- Consistent spacing and styling
- Real-time calculation displays
- Visual feedback for derived values
- Professional color-coded results

### Validation
- Min/max ranges on slider inputs
- Automatic calculation updates
- Error state handling
- Consistent formatting (currency, percentages)

## Technical Details

### File Structure
```
src/features/underwriting/
├── components/
│   ├── AssumptionsPresets.tsx (new)
│   ├── InputsTab.tsx (enhanced)
│   ├── ResultsTab.tsx (enhanced)
│   ├── UnderwritingModal.tsx (updated)
│   └── ... (other existing components)
├── hooks/
│   └── useUnderwriting.ts (enhanced)
└── utils/
    └── calculations.ts (new)

src/lib/calculations/
├── cashflow.ts (enhanced)
├── sensitivity.ts (enhanced)
└── irr.ts (existing)

src/types/
├── underwriting.ts (enhanced)
└── index.ts (updated exports)
```

### Dependencies
- React 19
- TypeScript
- Tailwind CSS
- Lucide Icons
- xlsx (for Excel export)

### Browser Storage
- Custom presets saved to localStorage
- JSON export/import for preset sharing
- Automatic preset indicators

## Testing Recommendations

1. **Input Validation**: Test min/max ranges on all sliders
2. **Calculations**: Verify all derived metrics (DSCR, IRR, etc.)
3. **Presets**: Test saving, loading, and importing/exporting
4. **Responsiveness**: Check layout on different screen sizes
5. **Export**: Verify PDF and Excel exports include new metrics

## Future Enhancements (Potential)

1. Rent roll upload for detailed unit-level analysis
2. Waterfall distribution modeling
3. Multiple exit scenarios comparison
4. Integration with market rent data APIs
5. Historical performance tracking
6. Portfolio-level aggregation
7. Debt structure optimization tool
8. Partnership equity allocation calculator
