import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Eye, Loader2, CheckCircle2, XCircle, ChevronRight, ChevronDown, Download,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GroupExtractionResponse } from '@/types/grouping';

interface DryRunPreviewProps {
  result: GroupExtractionResponse | null;
  groupName: string;
  onCommit: () => void;
  isLoading: boolean;
}

export function DryRunPreview({ result, groupName, onCommit, isLoading }: DryRunPreviewProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (!result && !isLoading) return null;

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400" />
          <p className="text-sm text-neutral-500 mt-2">Running dry-run extraction...</p>
        </CardContent>
      </Card>
    );
  }

  if (!result) return null;

  const successCount = result.files_processed - result.files_failed;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Dry Run Preview
            {result.dry_run && (
              <Badge variant="outline" className="ml-1">DRY RUN</Badge>
            )}
          </CardTitle>
          <Badge variant="secondary">{groupName}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg bg-neutral-50 p-3 text-center">
            <div className="text-xl font-semibold text-neutral-900">
              {result.files_processed}
            </div>
            <div className="text-xs text-neutral-500">Files Processed</div>
          </div>
          <div className="rounded-lg bg-green-50 p-3 text-center">
            <div className="flex items-center justify-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span className="text-xl font-semibold text-green-700">{successCount}</span>
            </div>
            <div className="text-xs text-neutral-500">Succeeded</div>
          </div>
          <div className="rounded-lg bg-red-50 p-3 text-center">
            <div className="flex items-center justify-center gap-1">
              <XCircle className="h-4 w-4 text-red-600" />
              <span className="text-xl font-semibold text-red-700">{result.files_failed}</span>
            </div>
            <div className="text-xs text-neutral-500">Failed</div>
          </div>
          <div className="rounded-lg bg-blue-50 p-3 text-center">
            <div className="text-xl font-semibold text-blue-700">
              {result.total_values.toLocaleString()}
            </div>
            <div className="text-xs text-neutral-500">Values Extracted</div>
          </div>
        </div>

        {/* Timing */}
        {result.started_at && result.completed_at && (
          <div className="text-xs text-neutral-500 flex items-center gap-4">
            <span>Started: {new Date(result.started_at).toLocaleTimeString()}</span>
            <span>Completed: {new Date(result.completed_at).toLocaleTimeString()}</span>
            <span>
              Duration: {(
                (new Date(result.completed_at).getTime() - new Date(result.started_at).getTime()) / 1000
              ).toFixed(1)}s
            </span>
          </div>
        )}

        {/* Toggle details button */}
        <button
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          {showDetails ? 'Hide details' : 'Show details'}
        </button>

        {showDetails && (
          <div className="border rounded-lg p-3 bg-neutral-50 text-sm space-y-1">
            <p className="text-neutral-700">
              <span className="font-medium">Group:</span> {result.group_name}
            </p>
            <p className="text-neutral-700">
              <span className="font-medium">Mode:</span>{' '}
              {result.dry_run ? 'Dry Run (no data written)' : 'Live Extraction'}
            </p>
            <p className={cn(
              'font-medium',
              result.files_failed > 0 ? 'text-amber-700' : 'text-green-700',
            )}>
              Success rate: {result.files_processed > 0
                ? ((successCount / result.files_processed) * 100).toFixed(0)
                : 0}%
            </p>
          </div>
        )}

        {/* Commit button */}
        {result.dry_run && (
          <div className="pt-2 border-t">
            <Button
              onClick={onCommit}
              disabled={isLoading || result.files_failed === result.files_processed}
              className="w-full"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Commit Extraction ({successCount} files)
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
