import { Search, Fingerprint, Map, AlertTriangle, Download, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PipelineStatus } from '@/types/grouping';

interface GroupPipelineStepperProps {
  status: PipelineStatus | null;
  isLoading: boolean;
}

const PHASES = [
  { key: 'discovery', label: 'Discovery', icon: Search },
  { key: 'fingerprint', label: 'Fingerprint & Group', icon: Fingerprint },
  { key: 'reference_map', label: 'Reference Map', icon: Map },
  { key: 'conflict_check', label: 'Conflict Check', icon: AlertTriangle },
  { key: 'extract', label: 'Extract', icon: Download },
  { key: 'validate', label: 'Validate', icon: CheckCircle2 },
] as const;

function getStepStatus(
  phaseKey: string,
  phases: Record<string, string>,
  phaseIndex: number,
): 'completed' | 'current' | 'pending' {
  const timestamp = phases[phaseKey];
  if (timestamp) return 'completed';

  // Current = first phase without a timestamp whose predecessor is completed
  const allKeys = PHASES.map((p) => p.key);
  const prevKey = phaseIndex > 0 ? allKeys[phaseIndex - 1] : null;

  if (phaseIndex === 0 || (prevKey && phases[prevKey])) {
    return 'current';
  }
  return 'pending';
}

export function GroupPipelineStepper({ status, isLoading }: GroupPipelineStepperProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-between px-4 py-6">
        {PHASES.map((_, i) => (
          <div key={i} className="flex items-center">
            <div className="h-10 w-10 rounded-full bg-neutral-200 animate-pulse" />
            {i < PHASES.length - 1 && (
              <div className="h-0.5 w-16 bg-neutral-200 mx-2" />
            )}
          </div>
        ))}
      </div>
    );
  }

  const phases = status?.phases ?? {};

  return (
    <div className="flex items-center justify-between px-2 py-4 overflow-x-auto">
      {PHASES.map((phase, idx) => {
        const stepStatus = status ? getStepStatus(phase.key, phases, idx) : 'pending';
        const Icon = phase.icon;
        const timestamp = phases[phase.key];

        return (
          <div key={phase.key} className="flex items-center flex-shrink-0">
            <div className="flex flex-col items-center gap-1.5 min-w-[90px]">
              <div
                className={cn(
                  'flex items-center justify-center h-10 w-10 rounded-full border-2 transition-colors',
                  stepStatus === 'completed' && 'bg-green-100 border-green-500 text-green-600',
                  stepStatus === 'current' && 'bg-blue-100 border-blue-500 text-blue-600',
                  stepStatus === 'pending' && 'bg-neutral-100 border-neutral-300 text-neutral-400',
                )}
              >
                {stepStatus === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : stepStatus === 'current' ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={cn(
                  'text-xs font-medium text-center leading-tight',
                  stepStatus === 'completed' && 'text-green-700',
                  stepStatus === 'current' && 'text-blue-700',
                  stepStatus === 'pending' && 'text-neutral-400',
                )}
              >
                {phase.label}
              </span>
              {timestamp && (
                <span className="text-[10px] text-neutral-400">
                  {new Date(timestamp).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>
            {idx < PHASES.length - 1 && (
              <div
                className={cn(
                  'h-0.5 w-12 mx-1 flex-shrink-0',
                  stepStatus === 'completed' ? 'bg-green-400' : 'bg-neutral-200',
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
