/**
 * Zod schemas for property API responses
 *
 * Validates raw JSON from /properties/dashboard and transforms
 * ISO date strings into Date objects. Replaces transformPropertyDates().
 *
 * All numeric fields use safeOptionalNum (coerces null/undefined/NaN → 0) so that
 * a single missing or malformed value does not reject the entire property.
 * Nested sub-objects are nullable/optional with sensible defaults so that
 * partially-populated DB rows (e.g. backfilled properties) still parse.
 */
import { z } from 'zod';
import { nullableDateString } from './common';

// ---------- Safe primitives ----------

/** Returns undefined for missing/invalid instead of 0.
 *  This preserves the distinction between "data missing" and "value is zero". */
const safeOptionalNum = z.preprocess(
  (v) => {
    if (v === null || v === undefined) return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  },
  z.number().optional(),
);

/** ISO date string → Date, with fallback to epoch for bad/missing values. */
const safeDateString = z.preprocess(
  (v) => {
    if (typeof v === 'string' && v.length > 0) {
      const d = new Date(v);
      return Number.isNaN(d.getTime()) ? new Date(0) : d;
    }
    return new Date(0);
  },
  z.date(),
);

/** Safe string: null/undefined → "" */
const safeStr = z.preprocess((v) => (typeof v === 'string' ? v : ''), z.string());

// ---------- Nested sub-schemas ----------

const addressSchema = z.object({
  street: safeStr,
  city: safeStr,
  state: safeStr,
  zip: safeStr,
  latitude: z.number().nullable().optional().default(null),
  longitude: z.number().nullable().optional().default(null),
  submarket: safeStr,
}).default({
  street: '', city: '', state: '', zip: '',
  latitude: null, longitude: null, submarket: '',
});

const propertyDetailsSchema = z.object({
  units: safeOptionalNum,
  squareFeet: safeOptionalNum,
  averageUnitSize: safeOptionalNum,
  yearBuilt: safeOptionalNum,
  propertyClass: z.enum(['A', 'B', 'C']).catch('C'),
  assetType: safeStr,
  amenities: z.array(z.string()).catch([]),
}).default({
  units: undefined, squareFeet: undefined, averageUnitSize: undefined, yearBuilt: undefined,
  propertyClass: 'C', assetType: '', amenities: [],
});

const acquisitionSchema = z.object({
  date: safeDateString,
  purchasePrice: safeOptionalNum,
  pricePerUnit: safeOptionalNum,
  closingCosts: safeOptionalNum,
  acquisitionFee: safeOptionalNum,
  totalInvested: safeOptionalNum,
  landAndAcquisitionCosts: safeOptionalNum,
  hardCosts: safeOptionalNum,
  softCosts: safeOptionalNum,
  lenderClosingCosts: safeOptionalNum,
  equityClosingCosts: safeOptionalNum,
  totalAcquisitionBudget: safeOptionalNum,
}).default({
  date: new Date(0), purchasePrice: undefined, pricePerUnit: undefined, closingCosts: undefined,
  acquisitionFee: undefined, totalInvested: undefined, landAndAcquisitionCosts: undefined,
  hardCosts: undefined, softCosts: undefined, lenderClosingCosts: undefined, equityClosingCosts: undefined,
  totalAcquisitionBudget: undefined,
});

const financingSchema = z.object({
  loanAmount: safeOptionalNum,
  loanToValue: safeOptionalNum,
  interestRate: safeOptionalNum,
  loanTerm: safeOptionalNum,
  amortization: safeOptionalNum,
  monthlyPayment: safeOptionalNum,
  lender: z.string().nullable().optional().default(null),
  originationDate: safeDateString,
  maturityDate: nullableDateString,
}).default({
  loanAmount: undefined, loanToValue: undefined, interestRate: undefined, loanTerm: undefined,
  amortization: undefined, monthlyPayment: undefined, lender: null,
  originationDate: new Date(0), maturityDate: null,
});

const valuationSchema = z.object({
  currentValue: safeOptionalNum,
  lastAppraisalDate: safeDateString,
  capRate: safeOptionalNum,
  appreciationSinceAcquisition: safeOptionalNum,
}).default({
  currentValue: undefined, lastAppraisalDate: new Date(0), capRate: undefined,
  appreciationSinceAcquisition: undefined,
});

const expensesSchema = z.object({
  realEstateTaxes: safeOptionalNum,
  otherExpenses: safeOptionalNum,
  propertyInsurance: safeOptionalNum,
  staffingPayroll: safeOptionalNum,
  propertyManagementFee: safeOptionalNum,
  repairsAndMaintenance: safeOptionalNum,
  turnover: safeOptionalNum,
  contractServices: safeOptionalNum,
  reservesForReplacement: safeOptionalNum,
  adminLegalSecurity: safeOptionalNum,
  advertisingLeasingMarketing: safeOptionalNum,
  total: safeOptionalNum,
}).default({
  realEstateTaxes: undefined, otherExpenses: undefined, propertyInsurance: undefined,
  staffingPayroll: undefined, propertyManagementFee: undefined, repairsAndMaintenance: undefined,
  turnover: undefined, contractServices: undefined, reservesForReplacement: undefined,
  adminLegalSecurity: undefined, advertisingLeasingMarketing: undefined, total: undefined,
});

const operationsSchema = z.object({
  occupancy: safeOptionalNum,
  averageRent: safeOptionalNum,
  rentPerSqft: safeOptionalNum,
  monthlyRevenue: safeOptionalNum,
  otherIncome: safeOptionalNum,
  expenses: expensesSchema,
  noi: safeOptionalNum,
  operatingExpenseRatio: safeOptionalNum,
  grossPotentialRevenue: safeOptionalNum,
  netRentalIncome: safeOptionalNum,
  otherIncomeAnnual: safeOptionalNum,
  vacancyLoss: safeOptionalNum,
  concessions: safeOptionalNum,
}).default({
  occupancy: undefined, averageRent: undefined, rentPerSqft: undefined, monthlyRevenue: undefined,
  otherIncome: undefined, expenses: {
    realEstateTaxes: undefined, otherExpenses: undefined, propertyInsurance: undefined,
    staffingPayroll: undefined, propertyManagementFee: undefined, repairsAndMaintenance: undefined,
    turnover: undefined, contractServices: undefined, reservesForReplacement: undefined,
    adminLegalSecurity: undefined, advertisingLeasingMarketing: undefined, total: undefined,
  }, noi: undefined, operatingExpenseRatio: undefined, grossPotentialRevenue: undefined,
  netRentalIncome: undefined, otherIncomeAnnual: undefined, vacancyLoss: undefined, concessions: undefined,
});

const operatingYearExpensesSchema = z.object({
  realEstateTaxes: safeOptionalNum,
  propertyInsurance: safeOptionalNum,
  staffingPayroll: safeOptionalNum,
  propertyManagementFee: safeOptionalNum,
  repairsAndMaintenance: safeOptionalNum,
  turnover: safeOptionalNum,
  contractServices: safeOptionalNum,
  reservesForReplacement: safeOptionalNum,
  adminLegalSecurity: safeOptionalNum,
  advertisingLeasingMarketing: safeOptionalNum,
  otherExpenses: safeOptionalNum,
  utilities: safeOptionalNum,
});

const operatingYearSchema = z.object({
  year: safeOptionalNum,
  grossPotentialRevenue: safeOptionalNum,
  lossToLease: safeOptionalNum,
  vacancyLoss: safeOptionalNum,
  badDebts: safeOptionalNum,
  concessions: safeOptionalNum,
  otherLoss: safeOptionalNum,
  netRentalIncome: safeOptionalNum,
  otherIncome: safeOptionalNum,
  laundryIncome: safeOptionalNum,
  parkingIncome: safeOptionalNum,
  petIncome: safeOptionalNum,
  storageIncome: safeOptionalNum,
  utilityIncome: safeOptionalNum,
  otherMiscIncome: safeOptionalNum,
  effectiveGrossIncome: safeOptionalNum,
  noi: safeOptionalNum,
  totalOperatingExpenses: safeOptionalNum,
  expenses: operatingYearExpensesSchema,
});

const performanceSchema = z.object({
  leveredIrr: safeOptionalNum,
  leveredMoic: safeOptionalNum,
  unleveredIrr: z.number().nullable().optional().default(null),
  unleveredMoic: z.number().nullable().optional().default(null),
  totalEquityCommitment: safeOptionalNum,
  totalCashFlowsToEquity: safeOptionalNum,
  netCashFlowsToEquity: safeOptionalNum,
  holdPeriodYears: safeOptionalNum,
  exitCapRate: safeOptionalNum,
  totalBasisPerUnitClose: safeOptionalNum,
  seniorLoanBasisPerUnitClose: safeOptionalNum,
  totalBasisPerUnitExit: z.number().nullable().optional().default(null),
  seniorLoanBasisPerUnitExit: z.number().nullable().optional().default(null),
}).default({
  leveredIrr: undefined, leveredMoic: undefined, unleveredIrr: null, unleveredMoic: null,
  totalEquityCommitment: undefined, totalCashFlowsToEquity: undefined, netCashFlowsToEquity: undefined,
  holdPeriodYears: undefined, exitCapRate: undefined, totalBasisPerUnitClose: undefined,
  seniorLoanBasisPerUnitClose: undefined, totalBasisPerUnitExit: null,
  seniorLoanBasisPerUnitExit: null,
});

const imagesSchema = z.object({
  main: safeStr,
  gallery: z.array(z.string()).catch([]),
}).default({ main: '', gallery: [] });

// ---------- Main property schema ----------

export const propertySchema = z.object({
  id: z.preprocess((v) => String(v ?? ''), z.string()),
  name: safeStr,
  address: addressSchema,
  propertyDetails: propertyDetailsSchema,
  acquisition: acquisitionSchema,
  financing: financingSchema,
  valuation: valuationSchema,
  operations: operationsSchema,
  operationsByYear: z.array(operatingYearSchema).catch([]),
  performance: performanceSchema,
  images: imagesSchema,
  lastAnalyzed: z.string().nullable().optional().transform((v) => v ?? undefined),
});

// ---------- Response schemas ----------

export const propertiesResponseSchema = z.object({
  properties: z.array(propertySchema),
  total: z.number(),
});

export const propertySummaryStatsSchema = z.object({
  totalProperties: safeOptionalNum,
  totalUnits: safeOptionalNum,
  totalValue: safeOptionalNum,
  totalInvested: safeOptionalNum,
  totalNOI: safeOptionalNum,
  averageOccupancy: safeOptionalNum,
  averageCapRate: safeOptionalNum,
  portfolioCashOnCash: safeOptionalNum,
  portfolioIRR: safeOptionalNum,
});
