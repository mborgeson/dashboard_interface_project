import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calculator, RotateCcw, Download, FileSpreadsheet } from 'lucide-react';
import { useUnderwriting } from '../hooks/useUnderwriting';
import { InputsTab } from './InputsTab';
import { ResultsTab } from './ResultsTab';
import { ProjectionsTab } from './ProjectionsTab';
import { SensitivityTab } from './SensitivityTab';
import { useToast } from '@/hooks/useToast';
import jsPDF from 'jspdf';
import * as XLSX from 'xlsx';

interface UnderwritingModalProps {
  trigger?: React.ReactNode;
}

export function UnderwritingModal({ trigger }: UnderwritingModalProps) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('inputs');
  const { inputs, updateInput, resetInputs, results, sensitivity } = useUnderwriting();
  const { success } = useToast();

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    if (tab === 'results' && results) {
      success('Analysis complete');
    }
  };

  const handleExportPDF = () => {
    if (!results) return;

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
    success('PDF exported', { description: 'Check your downloads' });
  };

  const handleExportExcel = () => {
    if (!results) return;

    const propertyName = inputs.propertyName || 'Investment Property';

    // Summary sheet
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

    // Projections sheet
    const projectionsData = [
      ['Year', 'Gross Income', 'Vacancy', 'EGI', 'OpEx', 'NOI', 'Debt Service', 'Cash Flow', 'Cumulative CF', 'Property Value', 'Loan Balance', 'Equity'],
      ...results.cashFlowProjection.map((p) => [
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
      ]),
    ];

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

    // Sensitivity sheet
    const sensitivityData = [
      ['Variable', 'Downside Scenario', 'Downside IRR', 'Base IRR', 'Upside IRR', 'Upside Scenario'],
      ...sensitivity.map((s) => [
        s.label,
        formatSensValue(s.name, s.lowValue),
        `${(s.lowIRR * 100).toFixed(2)}%`,
        `${(results.leveredIRR * 100).toFixed(2)}%`,
        `${(s.highIRR * 100).toFixed(2)}%`,
        formatSensValue(s.name, s.highValue),
      ]),
    ];

    const wb = XLSX.utils.book_new();
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
    const wsProjections = XLSX.utils.aoa_to_sheet(projectionsData);
    const wsSensitivity = XLSX.utils.aoa_to_sheet(sensitivityData);

    XLSX.utils.book_append_sheet(wb, wsSummary, 'Summary');
    XLSX.utils.book_append_sheet(wb, wsProjections, 'Projections');
    XLSX.utils.book_append_sheet(wb, wsSensitivity, 'Sensitivity');

    XLSX.writeFile(wb, `underwriting-${propertyName.replace(/\s+/g, '-').toLowerCase()}.xlsx`);
    success('Excel exported');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="default" size="sm" className="bg-accent-500 hover:bg-accent-600">
            <Calculator className="w-4 h-4 mr-2" />
            Underwrite Deal
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl font-semibold">
                {inputs.propertyName || 'New Investment Analysis'}
              </DialogTitle>
              <DialogDescription>
                Enter property details and financial assumptions to calculate returns
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={resetInputs}>
                <RotateCcw className="w-4 h-4 mr-1" />
                Reset
              </Button>
              {results && (
                <>
                  <Button variant="outline" size="sm" onClick={handleExportPDF}>
                    <Download className="w-4 h-4 mr-1" />
                    PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleExportExcel}>
                    <FileSpreadsheet className="w-4 h-4 mr-1" />
                    Excel
                  </Button>
                </>
              )}
            </div>
          </div>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="inputs">Inputs</TabsTrigger>
            <TabsTrigger value="results" disabled={!results}>
              Results
            </TabsTrigger>
            <TabsTrigger value="projections" disabled={!results}>
              Projections
            </TabsTrigger>
            <TabsTrigger value="sensitivity" disabled={!results}>
              Sensitivity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="inputs" className="mt-4">
            <InputsTab inputs={inputs} updateInput={updateInput} />
          </TabsContent>

          <TabsContent value="results" className="mt-4">
            {results && <ResultsTab results={results} />}
          </TabsContent>

          <TabsContent value="projections" className="mt-4">
            {results && <ProjectionsTab projections={results.cashFlowProjection} />}
          </TabsContent>

          <TabsContent value="sensitivity" className="mt-4">
            {results && sensitivity.length > 0 && (
              <SensitivityTab sensitivity={sensitivity} baseIRR={results.leveredIRR} />
            )}
          </TabsContent>
        </Tabs>

        {/* Quick Stats Bar */}
        {results && (
          <div className="mt-4 pt-4 border-t border-neutral-200">
            <div className="grid grid-cols-5 gap-4 text-center">
              <div>
                <div className="text-xs text-neutral-500">Levered IRR</div>
                <div className="text-lg font-semibold text-primary-600">
                  {(results.leveredIRR * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-500">Equity Multiple</div>
                <div className="text-lg font-semibold text-neutral-900">
                  {results.equityMultiple.toFixed(2)}x
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-500">Cash-on-Cash</div>
                <div className="text-lg font-semibold text-neutral-900">
                  {(results.year1.cashOnCashReturn * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-500">DSCR</div>
                <div className="text-lg font-semibold text-neutral-900">
                  {results.year1.debtServiceCoverageRatio.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-500">Total Equity</div>
                <div className="text-lg font-semibold text-neutral-900">
                  ${(results.totalEquityRequired / 1000000).toFixed(2)}M
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
