/**
 * Zod schemas for property API responses
 *
 * Validates raw JSON from /properties/dashboard and transforms
 * ISO date strings into Date objects. Replaces transformPropertyDates().
 *
 * All numeric fields use safeNum (coerces null/undefined/NaN → 0) so that
 * a single missing or malformed value does not reject the entire property.
 * Nested sub-objects are nullable/optional with sensible defaults so that
 * partially-populated DB rows (e.g. backfilled properties) still parse.
 */
import { z } from 'zod';
import { nullableDateString } from './common';

// ---------- Safe primitives ----------

/** Coerce any falsy / non-finite numeric input to 0. */
const safeNum = z.preprocess(
  (v) => {
    if (v === null || v === undefined) return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  },
  z.number(),
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
  units: safeNum,
  squareFeet: safeNum,
  averageUnitSize: safeNum,
  yearBuilt: safeNum,
  propertyClass: z.enum(['A', 'B', 'C']).catch('C'),
  assetType: safeStr,
  amenities: z.array(z.string()).catch([]),
}).default({
  units: 0, squareFeet: 0, averageUnitSize: 0, yearBuilt: 0,
  propertyClass: 'C', assetType: '', amenities: [],
});

const acquisitionSchema = z.object({
  date: safeDateString,
  purchasePrice: safeNum,
  pricePerUnit: safeNum,
  closingCosts: safeNum,
  acquisitionFee: safeNum,
  totalInvested: safeNum,
  landAndAcquisitionCosts: safeNum,
  hardCosts: safeNum,
  softCosts: safeNum,
  lenderClosingCosts: safeNum,
  equityClosingCosts: safeNum,
  totalAcquisitionBudget: safeNum,
}).default({
  date: new Date(0), purchasePrice: 0, pricePerUnit: 0, closingCosts: 0,
  acquisitionFee: 0, totalInvested: 0, landAndAcquisitionCosts: 0,
  hardCosts: 0, softCosts: 0, lenderClosingCosts: 0, equityClosingCosts: 0,
  totalAcquisitionBudget: 0,
});

const financingSchema = z.object({
  loanAmount: safeNum,
  loanToValue: safeNum,
  interestRate: safeNum,
  loanTerm: safeNum,
  amortization: safeNum,
  monthlyPayment: safeNum,
  lender: z.string().nullable().optional().default(null),
  originationDate: safeDateString,
  maturityDate: nullableDateString,
}).default({
  loanAmount: 0, loanToValue: 0, interestRate: 0, loanTerm: 0,
  amortization: 0, monthlyPayment: 0, lender: null,
  originationDate: new Date(0), maturityDate: null,
});

const valuationSchema = z.object({
  currentValue: safeNum,
  lastAppraisalDate: safeDateString,
  capRate: safeNum,
  appreciationSinceAcquisition: safeNum,
}).default({
  currentValue: 0, lastAppraisalDate: new Date(0), capRate: 0,
  appreciationSinceAcquisition: 0,
});

const expensesSchema = z.object({
  realEstateTaxes: safeNum,
  otherExpenses: safeNum,
  propertyInsurance: safeNum,
  staffingPayroll: safeNum,
  propertyManagementFee: safeNum,
  repairsAndMaintenance: safeNum,
  turnover: safeNum,
  contractServices: safeNum,
  reservesForReplacement: safeNum,
  adminLegalSecurity: safeNum,
  advertisingLeasingMarketing: safeNum,
  total: safeNum,
}).default({
  realEstateTaxes: 0, otherExpenses: 0, propertyInsurance: 0,
  staffingPayroll: 0, propertyManagementFee: 0, repairsAndMaintenance: 0,
  turnover: 0, contractServices: 0, reservesForReplacement: 0,
  adminLegalSecurity: 0, advertisingLeasingMarketing: 0, total: 0,
});

const operationsSchema = z.object({
  occupancy: safeNum,
  averageRent: safeNum,
  rentPerSqft: safeNum,
  monthlyRevenue: safeNum,
  otherIncome: safeNum,
  expenses: expensesSchema,
  noi: safeNum,
  operatingExpenseRatio: safeNum,
  grossPotentialRevenue: safeNum,
  netRentalIncome: safeNum,
  otherIncomeAnnual: safeNum,
  vacancyLoss: safeNum,
  concessions: safeNum,
}).default({
  occupancy: 0, averageRent: 0, rentPerSqft: 0, monthlyRevenue: 0,
  otherIncome: 0, expenses: {
    realEstateTaxes: 0, otherExpenses: 0, propertyInsurance: 0,
    staffingPayroll: 0, propertyManagementFee: 0, repairsAndMaintenance: 0,
    turnover: 0, contractServices: 0, reservesForReplacement: 0,
    adminLegalSecurity: 0, advertisingLeasingMarketing: 0, total: 0,
  }, noi: 0, operatingExpenseRatio: 0, grossPotentialRevenue: 0,
  netRentalIncome: 0, otherIncomeAnnual: 0, vacancyLoss: 0, concessions: 0,
});

const operatingYearExpensesSchema = z.object({
  realEstateTaxes: safeNum,
  propertyInsurance: safeNum,
  staffingPayroll: safeNum,
  propertyManagementFee: safeNum,
  repairsAndMaintenance: safeNum,
  turnover: safeNum,
  contractServices: safeNum,
  reservesForReplacement: safeNum,
  adminLegalSecurity: safeNum,
  advertisingLeasingMarketing: safeNum,
  otherExpenses: safeNum,
  utilities: safeNum,
});

const operatingYearSchema = z.object({
  year: safeNum,
  grossPotentialRevenue: safeNum,
  lossToLease: safeNum,
  vacancyLoss: safeNum,
  badDebts: safeNum,
  concessions: safeNum,
  otherLoss: safeNum,
  netRentalIncome: safeNum,
  otherIncome: safeNum,
  laundryIncome: safeNum,
  parkingIncome: safeNum,
  petIncome: safeNum,
  storageIncome: safeNum,
  utilityIncome: safeNum,
  otherMiscIncome: safeNum,
  effectiveGrossIncome: safeNum,
  noi: safeNum,
  totalOperatingExpenses: safeNum,
  expenses: operatingYearExpensesSchema,
});

const performanceSchema = z.object({
  leveredIrr: safeNum,
  leveredMoic: safeNum,
  unleveredIrr: z.number().nullable().optional().default(null),
  unleveredMoic: z.number().nullable().optional().default(null),
  totalEquityCommitment: safeNum,
  totalCashFlowsToEquity: safeNum,
  netCashFlowsToEquity: safeNum,
  holdPeriodYears: safeNum,
  exitCapRate: safeNum,
  totalBasisPerUnitClose: safeNum,
  seniorLoanBasisPerUnitClose: safeNum,
  totalBasisPerUnitExit: z.number().nullable().optional().default(null),
  seniorLoanBasisPerUnitExit: z.number().nullable().optional().default(null),
}).default({
  leveredIrr: 0, leveredMoic: 0, unleveredIrr: null, unleveredMoic: null,
  totalEquityCommitment: 0, totalCashFlowsToEquity: 0, netCashFlowsToEquity: 0,
  holdPeriodYears: 0, exitCapRate: 0, totalBasisPerUnitClose: 0,
  seniorLoanBasisPerUnitClose: 0, totalBasisPerUnitExit: null,
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
  totalProperties: safeNum,
  totalUnits: safeNum,
  totalValue: safeNum,
  totalInvested: safeNum,
  totalNOI: safeNum,
  averageOccupancy: safeNum,
  averageCapRate: safeNum,
  portfolioCashOnCash: safeNum,
  portfolioIRR: safeNum,
});
