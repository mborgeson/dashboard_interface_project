/**
 * WizardStepIndicator - Progress stepper for report wizard
 */
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export type WizardStep = 'template' | 'configure' | 'format' | 'generate';

interface WizardStepIndicatorProps {
  currentStep: WizardStep;
  completedSteps: WizardStep[];
}

interface StepConfig {
  id: WizardStep;
  label: string;
  shortLabel: string;
}

const STEPS: StepConfig[] = [
  { id: 'template', label: 'Select Template', shortLabel: 'Template' },
  { id: 'configure', label: 'Configure Parameters', shortLabel: 'Configure' },
  { id: 'format', label: 'Choose Format', shortLabel: 'Format' },
  { id: 'generate', label: 'Generate Report', shortLabel: 'Generate' },
];

export function WizardStepIndicator({
  currentStep,
  completedSteps,
}: WizardStepIndicatorProps) {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);

  return (
    <div className="flex items-center justify-between">
      {STEPS.map((step, index) => {
        const isCompleted = completedSteps.includes(step.id);
        const isCurrent = step.id === currentStep;
        const isPast = index < currentIndex;

        return (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step Circle */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : isCurrent
                      ? 'bg-blue-600 text-white'
                      : 'bg-neutral-200 text-neutral-500'
                )}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4" />
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={cn(
                  'mt-2 text-xs font-medium',
                  isCurrent ? 'text-blue-600' : 'text-neutral-500'
                )}
              >
                {step.shortLabel}
              </span>
            </div>

            {/* Connector Line */}
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  'flex-1 h-0.5 mx-2',
                  isPast || isCompleted ? 'bg-green-500' : 'bg-neutral-200'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
