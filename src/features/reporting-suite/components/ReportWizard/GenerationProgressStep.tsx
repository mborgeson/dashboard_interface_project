/**
 * GenerationProgressStep - Progress bar with polling and download
 */
import { Download, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { QueuedReport } from '@/hooks/api/useReporting';
import { cn } from '@/lib/utils';

interface GenerationProgressStepProps {
  report: QueuedReport | null;
  /** Reserved for future loading overlay indicator */
  isLoading?: boolean;
  error: Error | null;
  onDownload: () => void;
  onRetry: () => void;
}

export function GenerationProgressStep({
  report,
  error,
  onDownload,
  onRetry,
}: GenerationProgressStepProps) {
  // Calculate progress percentage
  const progress = report?.progress ?? 0;
  const status = report?.status ?? 'pending';

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <XCircle className="w-8 h-8 text-red-600" />
        </div>
        <h4 className="text-lg font-medium text-neutral-900 mb-2">Generation Failed</h4>
        <p className="text-sm text-neutral-500 mb-4 max-w-xs mx-auto">
          {error.message || 'An error occurred while generating the report. Please try again.'}
        </p>
        <Button onClick={onRetry} variant="outline">
          <AlertCircle className="w-4 h-4 mr-2" />
          Try Again
        </Button>
      </div>
    );
  }

  if (status === 'completed' && report) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-8 h-8 text-green-600" />
        </div>
        <h4 className="text-lg font-medium text-neutral-900 mb-2">Report Ready!</h4>
        <p className="text-sm text-neutral-500 mb-4">
          Your report has been generated successfully.
        </p>
        {report.fileSize && (
          <p className="text-xs text-neutral-400 mb-4">
            File size: {formatFileSize(report.fileSize)}
          </p>
        )}
        <Button onClick={onDownload}>
          <Download className="w-4 h-4 mr-2" />
          Download Report
        </Button>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <XCircle className="w-8 h-8 text-red-600" />
        </div>
        <h4 className="text-lg font-medium text-neutral-900 mb-2">Generation Failed</h4>
        <p className="text-sm text-neutral-500 mb-4 max-w-xs mx-auto">
          {report?.error || 'The report generation failed. Please try again.'}
        </p>
        <Button onClick={onRetry} variant="outline">
          <AlertCircle className="w-4 h-4 mr-2" />
          Try Again
        </Button>
      </div>
    );
  }

  // In progress states
  return (
    <div className="py-8">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
        <h4 className="text-lg font-medium text-neutral-900 mb-1">
          {getStatusLabel(status)}
        </h4>
        <p className="text-sm text-neutral-500">
          {getStatusDescription(status)}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="max-w-md mx-auto">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-neutral-600">Progress</span>
          <span className="text-sm font-medium text-neutral-900">{progress}%</span>
        </div>
        <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              progress < 100 ? 'bg-blue-500' : 'bg-green-500'
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
        {/* Estimated completion would go here if available */}
      </div>

      {/* Progress Steps */}
      <div className="mt-6 max-w-md mx-auto">
        <div className="space-y-2">
          <ProgressItem
            label="Initializing report"
            completed={progress >= 10}
            active={progress < 10}
          />
          <ProgressItem
            label="Fetching data"
            completed={progress >= 40}
            active={progress >= 10 && progress < 40}
          />
          <ProgressItem
            label="Processing calculations"
            completed={progress >= 70}
            active={progress >= 40 && progress < 70}
          />
          <ProgressItem
            label="Generating output"
            completed={progress >= 100}
            active={progress >= 70 && progress < 100}
          />
        </div>
      </div>
    </div>
  );
}

interface ProgressItemProps {
  label: string;
  completed: boolean;
  active: boolean;
}

function ProgressItem({ label, completed, active }: ProgressItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={cn(
          'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0',
          completed
            ? 'bg-green-500'
            : active
              ? 'bg-blue-500'
              : 'bg-neutral-200'
        )}
      >
        {completed ? (
          <CheckCircle className="w-3 h-3 text-white" />
        ) : active ? (
          <Loader2 className="w-3 h-3 text-white animate-spin" />
        ) : (
          <div className="w-2 h-2 bg-neutral-400 rounded-full" />
        )}
      </div>
      <span
        className={cn(
          'text-sm',
          completed
            ? 'text-green-700'
            : active
              ? 'text-blue-700 font-medium'
              : 'text-neutral-400'
        )}
      >
        {label}
      </span>
    </div>
  );
}

function getStatusLabel(status: QueuedReport['status']): string {
  switch (status) {
    case 'pending':
      return 'Initializing...';
    case 'generating':
      return 'Generating Report...';
    case 'completed':
      return 'Complete!';
    case 'failed':
      return 'Failed';
    default:
      return 'Processing...';
  }
}

function getStatusDescription(status: QueuedReport['status']): string {
  switch (status) {
    case 'pending':
      return 'Setting up report generation...';
    case 'generating':
      return 'Please wait while we generate your report';
    case 'completed':
      return 'Your report is ready for download';
    case 'failed':
      return 'An error occurred during generation';
    default:
      return 'Processing your request...';
  }
}

// fileSize from mock data is already formatted as string
function formatFileSize(fileSize: string): string {
  return fileSize;
}
