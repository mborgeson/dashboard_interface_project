/**
 * ReportWizard - Dialog wizard for report generation
 * 4-step wizard: Template → Configure → Format → Generate
 */
import { useState, useCallback, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import {
  useReportTemplatesWithMockFallback,
  useGenerateReportWithMockFallback,
  useQueuedReportWithMockFallback,
} from '@/hooks/api/useReporting';
import type { ReportTemplate, ReportFormat } from '@/hooks/api/useReporting';
import { WizardStepIndicator } from './WizardStepIndicator';
import type { WizardStep } from './WizardStepIndicator';
import { TemplateSelectionStep } from './TemplateSelectionStep';
import { ParameterConfigStep } from './ParameterConfigStep';
import { FormatSelectionStep } from './FormatSelectionStep';
import { GenerationProgressStep } from './GenerationProgressStep';
import { ChevronLeft, ChevronRight, FileText } from 'lucide-react';

interface ReportWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTemplateId?: string;
}

interface WizardState {
  step: WizardStep;
  completedSteps: WizardStep[];
  selectedTemplate: ReportTemplate | null;
  parameters: Record<string, unknown>;
  selectedFormat: ReportFormat | null;
  generatedReportId: string | null;
}

/**
 * Wrapper component that manages dialog state and reset key.
 * Uses key-based reset pattern to avoid setState in useEffect.
 */
export function ReportWizard({ open, onOpenChange, defaultTemplateId }: ReportWizardProps) {
  // Increment key when dialog closes to force fresh state on next open
  const [resetKey, setResetKey] = useState(0);

  const handleOpenChange = useCallback((newOpen: boolean) => {
    if (!newOpen) {
      // Dialog is closing - increment key for next open
      setResetKey((k) => k + 1);
    }
    onOpenChange(newOpen);
  }, [onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        {open && (
          <ReportWizardContent
            key={resetKey}
            defaultTemplateId={defaultTemplateId}
            onClose={() => handleOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

interface WizardContentProps {
  defaultTemplateId?: string;
  onClose: () => void;
}

function ReportWizardContent({ defaultTemplateId, onClose }: WizardContentProps) {
  // Fetch templates
  const { data: templates, isLoading: templatesLoading, error: templatesError, refetch } =
    useReportTemplatesWithMockFallback();

  // Compute initial state based on defaultTemplateId
  const initialState = useMemo((): WizardState => {
    if (defaultTemplateId && templates?.templates) {
      const template = templates.templates.find((t) => t.id === defaultTemplateId);
      if (template) {
        return {
          step: 'configure',
          completedSteps: ['template'],
          selectedTemplate: template,
          parameters: {},
          selectedFormat: null,
          generatedReportId: null,
        };
      }
    }
    return {
      step: 'template',
      completedSteps: [],
      selectedTemplate: null,
      parameters: {},
      selectedFormat: null,
      generatedReportId: null,
    };
  }, [defaultTemplateId, templates]);

  const [state, setState] = useState<WizardState>(initialState);
  const [paramErrors, setParamErrors] = useState<Record<string, string>>({});

  // Generate report mutation
  const generateMutation = useGenerateReportWithMockFallback();

  // Poll for report status (only when we have a report ID)
  const {
    data: queuedReport,
    isLoading: reportLoading,
    error: reportError,
  } = useQueuedReportWithMockFallback(state.generatedReportId, {
    refetchInterval: state.generatedReportId ? 2000 : undefined,
  });

  // Validation helper - must be declared before canGoNext
  const validateParameters = useCallback((): boolean => {
    if (!state.selectedTemplate) return false;

    const errors: Record<string, string> = {};
    for (const param of state.selectedTemplate.parameters) {
      if (param.required && !state.parameters[param.name]) {
        errors[param.name] = `${param.label} is required`;
      }
    }

    setParamErrors(errors);
    return Object.keys(errors).length === 0;
  }, [state.selectedTemplate, state.parameters]);

  // Generation helper - must be declared before goToNextStep
  const startGeneration = useCallback(async () => {
    if (!state.selectedTemplate || !state.selectedFormat) return;

    try {
      const result = await generateMutation.mutateAsync({
        templateId: state.selectedTemplate.id,
        format: state.selectedFormat,
        parameters: state.parameters,
      });
      setState((s) => ({ ...s, generatedReportId: result.id }));
    } catch (error) {
      console.error('Failed to start report generation:', error);
    }
  }, [state.selectedTemplate, state.selectedFormat, state.parameters, generateMutation]);

  // Navigation helpers
  const canGoNext = useCallback((): boolean => {
    switch (state.step) {
      case 'template':
        return state.selectedTemplate !== null;
      case 'configure':
        return validateParameters();
      case 'format':
        return state.selectedFormat !== null;
      case 'generate':
        return false;
      default:
        return false;
    }
  }, [state, validateParameters]);

  const goToNextStep = useCallback(() => {
    const steps: WizardStep[] = ['template', 'configure', 'format', 'generate'];
    const currentIndex = steps.indexOf(state.step);

    if (currentIndex < steps.length - 1) {
      const nextStep = steps[currentIndex + 1];
      setState((s) => ({
        ...s,
        step: nextStep,
        completedSteps: [...s.completedSteps.filter((cs) => cs !== s.step), s.step],
      }));

      // Start generation when entering the generate step
      if (nextStep === 'generate') {
        startGeneration();
      }
    }
  }, [state.step, startGeneration]);

  const goToPreviousStep = useCallback(() => {
    const steps: WizardStep[] = ['template', 'configure', 'format', 'generate'];
    const currentIndex = steps.indexOf(state.step);

    if (currentIndex > 0) {
      const prevStep = steps[currentIndex - 1];
      setState((s) => ({
        ...s,
        step: prevStep,
        completedSteps: s.completedSteps.filter((cs) => cs !== prevStep),
      }));
    }
  }, [state.step]);

  const handleDownload = useCallback(() => {
    if (queuedReport?.downloadUrl) {
      window.open(queuedReport.downloadUrl, '_blank');
    }
  }, [queuedReport]);

  const handleRetry = useCallback(() => {
    setState((s) => ({
      ...s,
      generatedReportId: null,
    }));
    startGeneration();
  }, [startGeneration]);

  // Render step content
  const renderStepContent = () => {
    if (templatesLoading) {
      return <WizardSkeleton />;
    }

    if (templatesError || !templates) {
      return (
        <div className="py-8">
          <ErrorState
            title="Failed to load templates"
            description="Unable to fetch report templates. Please try again."
            onRetry={() => refetch()}
          />
        </div>
      );
    }

    switch (state.step) {
      case 'template':
        return (
          <TemplateSelectionStep
            templates={templates.templates}
            selectedTemplateId={state.selectedTemplate?.id || null}
            onSelect={(template) => setState((s) => ({ ...s, selectedTemplate: template }))}
          />
        );

      case 'configure':
        if (!state.selectedTemplate) return null;
        return (
          <ParameterConfigStep
            template={state.selectedTemplate}
            values={state.parameters}
            onChange={(values) => setState((s) => ({ ...s, parameters: values }))}
            errors={paramErrors}
          />
        );

      case 'format':
        if (!state.selectedTemplate) return null;
        return (
          <FormatSelectionStep
            template={state.selectedTemplate}
            selectedFormat={state.selectedFormat}
            onSelect={(format) => setState((s) => ({ ...s, selectedFormat: format }))}
          />
        );

      case 'generate':
        return (
          <GenerationProgressStep
            report={queuedReport || null}
            isLoading={reportLoading || generateMutation.isPending}
            error={reportError || generateMutation.error}
            onDownload={handleDownload}
            onRetry={handleRetry}
          />
        );

      default:
        return null;
    }
  };

  const showBackButton = state.step !== 'template' && state.step !== 'generate';
  const showNextButton = state.step !== 'generate';
  const isGenerating = state.step === 'generate';

  return (
    <>
      <DialogHeader>
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-neutral-500" />
          <DialogTitle>Generate Report</DialogTitle>
        </div>
        <DialogDescription>
          Create a customized report from available templates
        </DialogDescription>
      </DialogHeader>

      {/* Step Indicator */}
      <div className="py-4 border-b border-neutral-200">
        <WizardStepIndicator
          currentStep={state.step}
          completedSteps={state.completedSteps}
        />
      </div>

      {/* Step Content */}
      <div className="py-4 min-h-[400px]">{renderStepContent()}</div>

      {/* Navigation */}
      {!isGenerating && (
        <div className="flex items-center justify-between pt-4 border-t border-neutral-200">
          <div>
            {showBackButton && (
              <Button variant="outline" onClick={goToPreviousStep}>
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              onClick={onClose}
            >
              Cancel
            </Button>
            {showNextButton && (
              <Button onClick={goToNextStep} disabled={!canGoNext()}>
                {state.step === 'format' ? 'Generate' : 'Next'}
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Close button when complete */}
      {isGenerating && queuedReport?.status === 'completed' && (
        <div className="flex items-center justify-center pt-4 border-t border-neutral-200">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      )}
    </>
  );
}

function WizardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    </div>
  );
}
