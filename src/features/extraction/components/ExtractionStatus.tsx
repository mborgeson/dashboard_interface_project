import { useExtractionStatus, useStartExtraction, getExtractionDuration } from '../hooks/useExtraction';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Play,
  Square,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  FileSpreadsheet,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExtractionStatus as ExtractionStatusType } from '@/types/extraction';

interface ExtractionStatusProps {
  onRunClick?: (runId: string) => void;
  className?: string;
}

function getStatusConfig(status: ExtractionStatusType) {
  switch (status) {
    case 'running':
      return {
        label: 'Running',
        icon: Loader2,
        variant: 'default' as const,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        animate: true,
      };
    case 'completed':
      return {
        label: 'Completed',
        icon: CheckCircle2,
        variant: 'secondary' as const,
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        animate: false,
      };
    case 'failed':
      return {
        label: 'Failed',
        icon: XCircle,
        variant: 'destructive' as const,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        animate: false,
      };
    case 'cancelled':
      return {
        label: 'Cancelled',
        icon: Square,
        variant: 'outline' as const,
        color: 'text-neutral-600',
        bgColor: 'bg-neutral-50',
        animate: false,
      };
  }
}

export function ExtractionStatus({ onRunClick, className }: ExtractionStatusProps) {
  const { currentRun, lastRun, stats, isLoading, error, refetch } = useExtractionStatus();
  const { startExtraction, cancelExtraction, isLoading: isActionLoading } = useStartExtraction();

  const handleStartExtraction = async () => {
    const result = await startExtraction();
    if (result) {
      refetch();
    }
  };

  const handleCancelExtraction = async () => {
    if (currentRun?.id) {
      const success = await cancelExtraction(currentRun.id);
      if (success) {
        refetch();
      }
    }
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Extraction Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
              <Skeleton className="h-16" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Extraction Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertTriangle className="h-10 w-10 text-amber-500 mb-2" />
            <p className="text-sm text-neutral-600 mb-4">{error.message}</p>
            <Button variant="outline" size="sm" onClick={refetch}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const activeRun = currentRun || lastRun;
  const statusConfig = activeRun ? getStatusConfig(activeRun.status) : null;

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Extraction Status
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={refetch}
              disabled={isLoading}
            >
              <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            </Button>
            {currentRun?.status === 'running' ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancelExtraction}
                disabled={isActionLoading}
              >
                <Square className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleStartExtraction}
                disabled={isActionLoading}
              >
                {isActionLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Start Extraction
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {activeRun && statusConfig ? (
          <div className="space-y-4">
            {/* Current/Last Run Status */}
            <div
              className={cn(
                "rounded-lg p-4 cursor-pointer transition-colors hover:opacity-90",
                statusConfig.bgColor
              )}
              onClick={() => onRunClick?.(activeRun.id)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <statusConfig.icon
                    className={cn(
                      "h-5 w-5",
                      statusConfig.color,
                      statusConfig.animate && "animate-spin"
                    )}
                  />
                  <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
                </div>
                <span className="text-sm text-neutral-500">
                  {new Date(activeRun.started_at).toLocaleString()}
                </span>
              </div>

              {/* Progress Bar for Running */}
              {activeRun.status === 'running' && activeRun.files_discovered > 0 && (
                <div className="mb-3">
                  <div className="flex justify-between text-sm text-neutral-600 mb-1">
                    <span>Processing files...</span>
                    <span>
                      {activeRun.files_processed} / {activeRun.files_discovered}
                    </span>
                  </div>
                  <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full transition-all duration-300"
                      style={{
                        width: `${(activeRun.files_processed / activeRun.files_discovered) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Stats Grid */}
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-semibold text-neutral-900">
                    {activeRun.files_discovered}
                  </div>
                  <div className="text-xs text-neutral-500">Discovered</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-green-600">
                    {activeRun.files_processed}
                  </div>
                  <div className="text-xs text-neutral-500">Processed</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-red-600">
                    {activeRun.files_failed}
                  </div>
                  <div className="text-xs text-neutral-500">Failed</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold text-neutral-700">
                    {getExtractionDuration(activeRun)}
                  </div>
                  <div className="text-xs text-neutral-500">Duration</div>
                </div>
              </div>
            </div>

            {/* Overall Stats */}
            {stats && (
              <div className="grid grid-cols-3 gap-4 pt-2 border-t">
                <div className="text-center">
                  <div className="text-lg font-semibold text-neutral-900">
                    {stats.total_runs}
                  </div>
                  <div className="text-xs text-neutral-500">Total Runs</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-neutral-900">
                    {stats.total_properties}
                  </div>
                  <div className="text-xs text-neutral-500">Properties</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-neutral-900">
                    {stats.total_fields_extracted.toLocaleString()}
                  </div>
                  <div className="text-xs text-neutral-500">Fields Extracted</div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Clock className="h-10 w-10 text-neutral-300 mb-2" />
            <p className="text-sm text-neutral-600 mb-4">No extraction runs yet</p>
            <Button onClick={handleStartExtraction} disabled={isActionLoading}>
              {isActionLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Start First Extraction
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
