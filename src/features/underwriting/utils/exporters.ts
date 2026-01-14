/**
 * Lazy-loaded export utilities for underwriting analysis
 *
 * These functions dynamically import jsPDF and ExcelJS only when needed,
 * reducing initial bundle size by ~52MB for users who don't export.
 */

import type { UnderwritingInputs, UnderwritingResults, SensitivityVariable } from '@/types';

/**
 * Export underwriting analysis to PDF format
 * Dynamically loads jsPDF (~2.5MB) only when called
 */
export async function exportToPDF(
  inputs: UnderwritingInputs,
  results: UnderwritingResults
): Promise<void> {
  // Dynamic import - jsPDF is only loaded when user clicks export
  const { default: jsPDF } = await import('jspdf');

  const doc = new jsPDF();
  const propertyName = inputs.propertyName || 'Investment Property';

  // Title
  doc.setFontSize(20);
  doc.text(`Underwriting Analysis: ${propertyName}`, 20, 20);

  // Key Metrics
  doc.setFontSize(14);
  doc.text('Key Return Metrics', 20, 40);
  doc.setFontSize(10);
  doc.text(`Levered IRR: ${(results.leveredIRR * 100).toFixed(2)}%`, 25, 50);
  doc.text(`Unlevered IRR: ${(results.unleveredIRR * 100).toFixed(2)}%`, 25, 57);
  doc.text(`Equity Multiple: ${results.equityMultiple.toFixed(2)}x`, 25, 64);
  doc.text(`Average Annual Return: ${(results.averageAnnualReturn * 100).toFixed(2)}%`, 25, 71);

  // Acquisition
  doc.setFontSize(14);
  doc.text('Acquisition Metrics', 20, 88);
  doc.setFontSize(10);
  doc.text(`Total Equity Required: $${results.totalEquityRequired.toLocaleString()}`, 25, 98);
  doc.text(`Loan Amount: $${results.loanAmount.toLocaleString()}`, 25, 105);
  doc.text(`Closing Costs: $${results.closingCosts.toLocaleString()}`, 25, 112);

  // Year 1
  doc.setFontSize(14);
  doc.text('Year 1 Performance', 20, 129);
  doc.setFontSize(10);
  doc.text(`Net Operating Income: $${results.year1.noi.toLocaleString()}`, 25, 139);
  doc.text(`Cash Flow: $${results.year1.cashFlow.toLocaleString()}`, 25, 146);
  doc.text(`Cash-on-Cash Return: ${(results.year1.cashOnCashReturn * 100).toFixed(2)}%`, 25, 153);
  doc.text(`DSCR: ${results.year1.debtServiceCoverageRatio.toFixed(2)}`, 25, 160);

  // Exit
  doc.setFontSize(14);
  doc.text('Exit Analysis', 20, 177);
  doc.setFontSize(10);
  doc.text(`Exit Value: $${results.exitValue.toLocaleString()}`, 25, 187);
  doc.text(`Sale Proceeds: $${results.saleProceeds.toLocaleString()}`, 25, 194);
  doc.text(`Total Profit: $${results.totalProfit.toLocaleString()}`, 25, 201);

  // Footer
  doc.setFontSize(8);
  doc.text(`Generated: ${new Date().toLocaleDateString()} | B&R Capital Analytics`, 20, 280);

  doc.save(`underwriting-${propertyName.replace(/\s+/g, '-').toLowerCase()}.pdf`);
}

/**
 * Export underwriting analysis to Excel format
 * Dynamically loads ExcelJS (~49MB) only when called
 */
export async function exportToExcel(
  inputs: UnderwritingInputs,
  results: UnderwritingResults,
  sensitivity: SensitivityVariable[]
): Promise<void> {
  // Dynamic import - ExcelJS is only loaded when user clicks export
  const ExcelJS = await import('exceljs');

  const propertyName = inputs.propertyName || 'Investment Property';

  // Helper to format sensitivity values
  const formatSensValue = (name: string, value: number): string => {
    if (name.includes('Percent') || name.includes('Rate') || name === 'exitCapRate') {
      return `${(value * 100).toFixed(2)}%`;
    }
    if (name.includes('PerUnit') || name === 'currentRentPerUnit') {
      return `$${value.toLocaleString()}`;
    }
    return value.toFixed(1);
  };

  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'B&R Capital Analytics';
  workbook.created = new Date();

  // Summary sheet
  const summarySheet = workbook.addWorksheet('Summary');
  const summaryData = [
    ['Underwriting Analysis', propertyName],
    [''],
    ['Key Return Metrics'],
    ['Levered IRR', `${(results.leveredIRR * 100).toFixed(2)}%`],
    ['Unlevered IRR', `${(results.unleveredIRR * 100).toFixed(2)}%`],
    ['Equity Multiple', `${results.equityMultiple.toFixed(2)}x`],
    ['Average Annual Return', `${(results.averageAnnualReturn * 100).toFixed(2)}%`],
    [''],
    ['Acquisition Metrics'],
    ['Down Payment', results.downPayment],
    ['Loan Amount', results.loanAmount],
    ['Closing Costs', results.closingCosts],
    ['Total Equity Required', results.totalEquityRequired],
    [''],
    ['Year 1 Performance'],
    ['Gross Income', results.year1.grossIncome],
    ['Vacancy', results.year1.vacancy],
    ['Effective Gross Income', results.year1.effectiveGrossIncome],
    ['Operating Expenses', results.year1.operatingExpenses],
    ['NOI', results.year1.noi],
    ['Debt Service', results.year1.debtService],
    ['Cash Flow', results.year1.cashFlow],
    ['Cash-on-Cash Return', `${(results.year1.cashOnCashReturn * 100).toFixed(2)}%`],
    ['DSCR', results.year1.debtServiceCoverageRatio.toFixed(2)],
    [''],
    ['Exit Analysis'],
    ['Exit Value', results.exitValue],
    ['Loan Paydown', results.loanPaydown],
    ['Sale Proceeds', results.saleProceeds],
    ['Total Profit', results.totalProfit],
  ];
  summaryData.forEach((row) => summarySheet.addRow(row));

  // Projections sheet
  const projectionsSheet = workbook.addWorksheet('Projections');
  projectionsSheet.addRow(['Year', 'Gross Income', 'Vacancy', 'EGI', 'OpEx', 'NOI', 'Debt Service', 'Cash Flow', 'Cumulative CF', 'Property Value', 'Loan Balance', 'Equity']);
  results.cashFlowProjection.forEach((p) => {
    projectionsSheet.addRow([
      p.year,
      p.grossIncome,
      p.vacancy,
      p.effectiveGrossIncome,
      p.operatingExpenses,
      p.noi,
      p.debtService,
      p.cashFlow,
      p.cumulativeCashFlow,
      p.propertyValue,
      p.loanBalance,
      p.equity,
    ]);
  });

  // Sensitivity sheet
  const sensitivitySheet = workbook.addWorksheet('Sensitivity');
  sensitivitySheet.addRow(['Variable', 'Downside Scenario', 'Downside IRR', 'Base IRR', 'Upside IRR', 'Upside Scenario']);
  sensitivity.forEach((s) => {
    sensitivitySheet.addRow([
      s.label,
      formatSensValue(s.name, s.lowValue),
      `${(s.lowIRR * 100).toFixed(2)}%`,
      `${(results.leveredIRR * 100).toFixed(2)}%`,
      `${(s.highIRR * 100).toFixed(2)}%`,
      formatSensValue(s.name, s.highValue),
    ]);
  });

  // Generate and download file
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `underwriting-${propertyName.replace(/\s+/g, '-').toLowerCase()}.xlsx`;
  link.click();
  window.URL.revokeObjectURL(url);
}
