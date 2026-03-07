import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMapFilters } from '../hooks/useMapFilters';
import type { Property } from '@/types';

// Minimal property factory -- only fields the hook actually reads
function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'prop-1',
    name: 'Test',
    address: {
      street: '1 Main',
      city: 'Phoenix',
      state: 'AZ',
      zip: '85001',
      latitude: 33.5,
      longitude: -112.1,
      submarket: 'Tempe',
    },
    propertyDetails: {
      units: 100,
      squareFeet: 80000,
      averageUnitSize: 800,
      yearBuilt: 2000,
      propertyClass: 'A',
      assetType: 'Multifamily',
      amenities: [],
    },
    acquisition: {
      date: new Date(),
      purchasePrice: 10000000,
      pricePerUnit: 100000,
      closingCosts: 0,
      acquisitionFee: 0,
      totalInvested: 5000000,
      landAndAcquisitionCosts: 0,
      hardCosts: 0,
      softCosts: 0,
      lenderClosingCosts: 0,
      equityClosingCosts: 0,
      totalAcquisitionBudget: 10000000,
    },
    financing: {
      loanAmount: 7000000,
      loanToValue: 0.7,
      interestRate: 0.04,
      loanTerm: 10,
      amortization: 30,
      monthlyPayment: 33000,
      lender: null,
      originationDate: new Date(),
      maturityDate: null,
    },
    valuation: {
      currentValue: 12000000,
      lastAppraisalDate: new Date(),
      capRate: 0.05,
      appreciationSinceAcquisition: 0.2,
    },
    operations: {
      occupancy: 0.93,
      averageRent: 1100,
      rentPerSqft: 1.4,
      monthlyRevenue: 100000,
      otherIncome: 5000,
      expenses: {
        realEstateTaxes: 100000,
        otherExpenses: 20000,
        propertyInsurance: 30000,
        staffingPayroll: 80000,
        propertyManagementFee: 40000,
        repairsAndMaintenance: 25000,
        turnover: 10000,
        contractServices: 15000,
        reservesForReplacement: 20000,
        adminLegalSecurity: 10000,
        advertisingLeasingMarketing: 8000,
        total: 358000,
      },
      noi: 842000,
      operatingExpenseRatio: 0.3,
      grossPotentialRevenue: 1200000,
      netRentalIncome: 1100000,
      otherIncomeAnnual: 60000,
      vacancyLoss: 100000,
      concessions: 0,
    },
    operationsByYear: [],
    performance: {
      leveredIrr: 0.12,
      leveredMoic: 1.8,
      unleveredIrr: 0.08,
      unleveredMoic: 1.4,
      totalEquityCommitment: 5000000,
      totalCashFlowsToEquity: 9000000,
      netCashFlowsToEquity: 4000000,
      holdPeriodYears: 5,
      exitCapRate: 0.05,
      totalBasisPerUnitClose: 100000,
      seniorLoanBasisPerUnitClose: 70000,
      totalBasisPerUnitExit: null,
      seniorLoanBasisPerUnitExit: null,
    },
    images: { main: '', gallery: [] },
    ...overrides,
  } as Property;
}

describe('useMapFilters', () => {
  it('excludes properties with null coordinates', () => {
    const properties = [
      makeProperty({ id: 'a', address: { ...makeProperty().address, latitude: 33.5, longitude: -112.1 } }),
      makeProperty({ id: 'b', address: { ...makeProperty().address, latitude: null, longitude: null } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    expect(result.current.mappableProperties).toHaveLength(1);
    expect(result.current.mappableProperties[0].id).toBe('a');
    expect(result.current.excludedCoordinateCount).toBe(1);
  });

  it('excludes properties with fallback Phoenix center coordinates (33.45, -112.07)', () => {
    const properties = [
      makeProperty({ id: 'real', address: { ...makeProperty().address, latitude: 33.5, longitude: -112.1 } }),
      makeProperty({ id: 'fallback', address: { ...makeProperty().address, latitude: 33.45, longitude: -112.07 } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    expect(result.current.mappableProperties).toHaveLength(1);
    expect(result.current.mappableProperties[0].id).toBe('real');
    expect(result.current.excludedCoordinateCount).toBe(1);
  });

  it('includes all properties when all have valid coordinates', () => {
    const properties = [
      makeProperty({ id: 'a', address: { ...makeProperty().address, latitude: 33.5, longitude: -112.1 } }),
      makeProperty({ id: 'b', address: { ...makeProperty().address, latitude: 33.6, longitude: -112.2 } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    expect(result.current.mappableProperties).toHaveLength(2);
    expect(result.current.excludedCoordinateCount).toBe(0);
  });

  it('filters by property class', () => {
    const properties = [
      makeProperty({ id: 'a', propertyDetails: { ...makeProperty().propertyDetails, propertyClass: 'A' } }),
      makeProperty({ id: 'b', propertyDetails: { ...makeProperty().propertyDetails, propertyClass: 'B' } }),
      makeProperty({ id: 'c', propertyDetails: { ...makeProperty().propertyDetails, propertyClass: 'C' } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    // All included initially
    expect(result.current.filteredProperties).toHaveLength(3);

    // Toggle off Class A
    act(() => result.current.togglePropertyClass('A'));
    expect(result.current.filteredProperties).toHaveLength(2);
    expect(result.current.filteredProperties.every(p => p.propertyDetails.propertyClass !== 'A')).toBe(true);
  });

  it('returns correct value range', () => {
    const properties = [
      makeProperty({ valuation: { ...makeProperty().valuation, currentValue: 5000000 } }),
      makeProperty({ valuation: { ...makeProperty().valuation, currentValue: 20000000 } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    expect(result.current.valueRange).toEqual([5000000, 20000000]);
  });

  it('handles empty property list', () => {
    const { result } = renderHook(() => useMapFilters([]));
    expect(result.current.filteredProperties).toHaveLength(0);
    expect(result.current.mappableProperties).toHaveLength(0);
    expect(result.current.excludedCoordinateCount).toBe(0);
    expect(result.current.valueRange).toEqual([0, 100000000]);
  });

  it('resetFilters restores all defaults', () => {
    const properties = [
      makeProperty({ id: 'a', propertyDetails: { ...makeProperty().propertyDetails, propertyClass: 'A' } }),
    ];

    const { result } = renderHook(() => useMapFilters(properties));
    act(() => result.current.togglePropertyClass('A'));
    expect(result.current.filteredProperties).toHaveLength(0);

    act(() => result.current.resetFilters());
    expect(result.current.filteredProperties).toHaveLength(1);
  });
});
