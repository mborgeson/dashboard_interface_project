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

function QuickStatItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: 'green' | 'amber' | 'red' | 'default';
}) {
  const colorClasses = {
    green: 'text-green-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    default: 'text-white',
  };

  return (
    <div className="text-center">
      <div className="text-xs text-neutral-400 uppercase tracking-wider mb-0.5">{label}</div>
      <div className={`text-xl font-bold ${colorClasses[color ?? 'default']}`}>{value}</div>
    </div>
  );
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

  // Color-code IRR
  const irrColor = results
    ? results.leveredIRR >= 0.15
      ? 'green'
      : results.leveredIRR >= 0.08
        ? 'amber'
        : 'red'
    : 'default';

  // Color-code equity multiple
  const emColor = results
    ? results.equityMultiple >= 2.0
      ? 'green'
      : results.equityMultiple >= 1.5
        ? 'amber'
        : 'red'
    : 'default';

  // Color-code DSCR
  const dscrColor = results
    ? results.year1.debtServiceCoverageRatio >= 1.25
      ? 'green'
      : results.year1.debtServiceCoverageRatio >= 1.0
        ? 'amber'
        : 'red'
    : 'default';

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="default" size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
            <Calculator className="w-4 h-4 mr-2" />
            Underwrite Deal
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-6xl w-[95vw] max-h-[90vh] flex flex-col p-0 gap-0 bg-white">
        {/* Header */}
        <DialogHeader className="flex-shrink-0 px-6 pt-5 pb-3 border-b border-neutral-200">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl font-semibold text-primary-700">
                {inputs.propertyName || 'New Investment Analysis'}
              </DialogTitle>
              <DialogDescription className="text-sm text-neutral-500 mt-0.5">
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

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col min-h-0 px-6">
          <TabsList className="grid w-full grid-cols-4 mt-3 mb-3 bg-neutral-100 p-1 rounded-lg">
            <TabsTrigger
              value="inputs"
              className="data-[state=active]:bg-white data-[state=active]:text-primary-700 data-[state=active]:shadow-sm rounded-md py-2 text-sm font-medium"
            >
              Inputs
            </TabsTrigger>
            <TabsTrigger
              value="results"
              disabled={!results}
              className="data-[state=active]:bg-white data-[state=active]:text-primary-700 data-[state=active]:shadow-sm rounded-md py-2 text-sm font-medium"
            >
              Results
            </TabsTrigger>
            <TabsTrigger
              value="projections"
              disabled={!results}
              className="data-[state=active]:bg-white data-[state=active]:text-primary-700 data-[state=active]:shadow-sm rounded-md py-2 text-sm font-medium"
            >
              Projections
            </TabsTrigger>
            <TabsTrigger
              value="sensitivity"
              disabled={!results}
              className="data-[state=active]:bg-white data-[state=active]:text-primary-700 data-[state=active]:shadow-sm rounded-md py-2 text-sm font-medium"
            >
              Sensitivity
            </TabsTrigger>
          </TabsList>

          {/* Scrollable content area — single scroll context */}
          <div className="flex-1 overflow-y-auto min-h-0 pb-4">
            <TabsContent value="inputs" className="mt-0 data-[state=active]:block">
              <InputsTab inputs={inputs} updateInput={updateInput} />
            </TabsContent>

            <TabsContent value="results" className="mt-0 data-[state=active]:block">
              {results && <ResultsTab results={results} />}
            </TabsContent>

            <TabsContent value="projections" className="mt-0 data-[state=active]:block">
              {results && <ProjectionsTab projections={results.cashFlowProjection} />}
            </TabsContent>

            <TabsContent value="sensitivity" className="mt-0 data-[state=active]:block">
              {results && sensitivity.length > 0 && (
                <SensitivityTab sensitivity={sensitivity} baseIRR={results.leveredIRR} />
              )}
            </TabsContent>
          </div>
        </Tabs>

        {/* Sticky Quick Stats Bar */}
        {results && (
          <div className="flex-shrink-0 bg-neutral-900 border-t border-neutral-700 px-6 py-3">
            <div className="grid grid-cols-5 gap-6">
              <QuickStatItem
                label="Levered IRR"
                value={`${(results.leveredIRR * 100).toFixed(1)}%`}
                color={irrColor}
              />
              <QuickStatItem
                label="Equity Multiple"
                value={`${results.equityMultiple.toFixed(2)}x`}
                color={emColor}
              />
              <QuickStatItem
                label="Cash-on-Cash"
                value={`${(results.year1.cashOnCashReturn * 100).toFixed(1)}%`}
              />
              <QuickStatItem
                label="DSCR"
                value={results.year1.debtServiceCoverageRatio.toFixed(2)}
                color={dscrColor}
              />
              <QuickStatItem
                label="Total Equity"
                value={`$${(results.totalEquityRequired / 1000000).toFixed(2)}M`}
              />
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
