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
import { Calculator, RotateCcw, Download, FileSpreadsheet, Loader2 } from 'lucide-react';
import { useUnderwriting } from '../hooks/useUnderwriting';
import { InputsTab } from './InputsTab';
import { ResultsTab } from './ResultsTab';
import { ProjectionsTab } from './ProjectionsTab';
import { SensitivityTab } from './SensitivityTab';
import { useToast } from '@/hooks/useToast';
import { exportToPDF, exportToExcel } from '../utils/exporters';

interface UnderwritingModalProps {
  trigger?: React.ReactNode;
}

export function UnderwritingModal({ trigger }: UnderwritingModalProps) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('inputs');
  const [isExportingPDF, setIsExportingPDF] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const { inputs, updateInput, resetInputs, results, sensitivity } = useUnderwriting();
  const { success, error } = useToast();

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    if (tab === 'results' && results) {
      success('Analysis complete');
    }
  };

  const handleExportPDF = async () => {
    if (!results) return;

    setIsExportingPDF(true);
    try {
      await exportToPDF(inputs, results);
      success('PDF exported', { description: 'Check your downloads' });
    } catch (err) {
      console.error('PDF export failed:', err);
      error('Export failed', { description: 'Could not generate PDF' });
    } finally {
      setIsExportingPDF(false);
    }
  };

  const handleExportExcel = async () => {
    if (!results) return;

    setIsExportingExcel(true);
    try {
      await exportToExcel(inputs, results, sensitivity);
      success('Excel exported', { description: 'Check your downloads' });
    } catch (err) {
      console.error('Excel export failed:', err);
      error('Export failed', { description: 'Could not generate Excel file' });
    } finally {
      setIsExportingExcel(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="default" size="sm" className="bg-accent-600 hover:bg-accent-700">
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExportPDF}
                    disabled={isExportingPDF}
                  >
                    {isExportingPDF ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 mr-1" />
                    )}
                    PDF
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExportExcel}
                    disabled={isExportingExcel}
                  >
                    {isExportingExcel ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <FileSpreadsheet className="w-4 h-4 mr-1" />
                    )}
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
