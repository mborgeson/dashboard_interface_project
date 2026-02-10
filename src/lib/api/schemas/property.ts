/**
 * Zod schemas for property API responses
 *
 * Validates raw JSON from /properties/dashboard and transforms
 * ISO date strings into Date objects. Replaces transformPropertyDates().
 */
import { z } from 'zod';
import { dateString, nullableDateString } from './common';

// ---------- Nested sub-schemas ----------

const addressSchema = z.object({
  street: z.string(),
  city: z.string(),
  state: z.string(),
  zip: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  submarket: z.string(),
});

const propertyDetailsSchema = z.object({
  units: z.number(),
  squareFeet: z.number(),
  averageUnitSize: z.number(),
  yearBuilt: z.number(),
  propertyClass: z.enum(['A', 'B', 'C']),
  assetType: z.string(),
  amenities: z.array(z.string()),
});

const acquisitionSchema = z.object({
  date: dateString,
  purchasePrice: z.number(),
  pricePerUnit: z.number(),
  closingCosts: z.number(),
  acquisitionFee: z.number(),
  totalInvested: z.number(),
  landAndAcquisitionCosts: z.number(),
  hardCosts: z.number(),
  softCosts: z.number(),
  lenderClosingCosts: z.number(),
  equityClosingCosts: z.number(),
  totalAcquisitionBudget: z.number(),
});

const financingSchema = z.object({
  loanAmount: z.number(),
  loanToValue: z.number(),
  interestRate: z.number(),
  loanTerm: z.number(),
  amortization: z.number(),
  monthlyPayment: z.number(),
  lender: z.string().nullable(),
  originationDate: dateString,
  maturityDate: nullableDateString,
});

const valuationSchema = z.object({
  currentValue: z.number(),
  lastAppraisalDate: dateString,
  capRate: z.number(),
  appreciationSinceAcquisition: z.number(),
});

const expensesSchema = z.object({
  realEstateTaxes: z.number(),
  otherExpenses: z.number(),
  propertyInsurance: z.number(),
  staffingPayroll: z.number(),
  propertyManagementFee: z.number(),
  repairsAndMaintenance: z.number(),
  turnover: z.number(),
  contractServices: z.number(),
  reservesForReplacement: z.number(),
  adminLegalSecurity: z.number(),
  advertisingLeasingMarketing: z.number(),
  total: z.number(),
});

const operationsSchema = z.object({
  occupancy: z.number(),
  averageRent: z.number(),
  rentPerSqft: z.number(),
  monthlyRevenue: z.number(),
  otherIncome: z.number(),
  expenses: expensesSchema,
  noi: z.number(),
  operatingExpenseRatio: z.number(),
  grossPotentialRevenue: z.number(),
  netRentalIncome: z.number(),
  otherIncomeAnnual: z.number(),
  vacancyLoss: z.number(),
  concessions: z.number(),
});

const operatingYearExpensesSchema = z.object({
  realEstateTaxes: z.number(),
  propertyInsurance: z.number(),
  staffingPayroll: z.number(),
  propertyManagementFee: z.number(),
  repairsAndMaintenance: z.number(),
  turnover: z.number(),
  contractServices: z.number(),
  reservesForReplacement: z.number(),
  adminLegalSecurity: z.number(),
  advertisingLeasingMarketing: z.number(),
  otherExpenses: z.number(),
  utilities: z.number(),
});

const operatingYearSchema = z.object({
  year: z.number(),
  grossPotentialRevenue: z.number(),
  lossToLease: z.number(),
  vacancyLoss: z.number(),
  badDebts: z.number(),
  concessions: z.number(),
  otherLoss: z.number(),
  netRentalIncome: z.number(),
  otherIncome: z.number(),
  laundryIncome: z.number(),
  parkingIncome: z.number(),
  petIncome: z.number(),
  storageIncome: z.number(),
  utilityIncome: z.number(),
  otherMiscIncome: z.number(),
  effectiveGrossIncome: z.number(),
  noi: z.number(),
  totalOperatingExpenses: z.number(),
  expenses: operatingYearExpensesSchema,
});

const performanceSchema = z.object({
  leveredIrr: z.number(),
  leveredMoic: z.number(),
  unleveredIrr: z.number().nullable(),
  unleveredMoic: z.number().nullable(),
  totalEquityCommitment: z.number(),
  totalCashFlowsToEquity: z.number(),
  netCashFlowsToEquity: z.number(),
  holdPeriodYears: z.number(),
  exitCapRate: z.number(),
  totalBasisPerUnitClose: z.number(),
  seniorLoanBasisPerUnitClose: z.number(),
  totalBasisPerUnitExit: z.number().nullable(),
  seniorLoanBasisPerUnitExit: z.number().nullable(),
});

const imagesSchema = z.object({
  main: z.string(),
  gallery: z.array(z.string()),
});

// ---------- Main property schema ----------

export const propertySchema = z.object({
  id: z.string(),
  name: z.string(),
  address: addressSchema,
  propertyDetails: propertyDetailsSchema,
  acquisition: acquisitionSchema,
  financing: financingSchema,
  valuation: valuationSchema,
  operations: operationsSchema,
  operationsByYear: z.array(operatingYearSchema),
  performance: performanceSchema,
  images: imagesSchema,
});

// ---------- Response schemas ----------

export const propertiesResponseSchema = z.object({
  properties: z.array(propertySchema),
  total: z.number(),
});

export const propertySummaryStatsSchema = z.object({
  totalProperties: z.number(),
  totalUnits: z.number(),
  totalValue: z.number(),
  totalInvested: z.number(),
  totalNOI: z.number(),
  averageOccupancy: z.number(),
  averageCapRate: z.number(),
  portfolioCashOnCash: z.number(),
  portfolioIRR: z.number(),
});
