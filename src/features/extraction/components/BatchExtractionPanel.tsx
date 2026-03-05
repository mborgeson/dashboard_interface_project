import { useState } from 'react';
import { useRunBatchExtraction } from '../hooks/useGroupPipeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Zap, Loader2, CheckCircle2, XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GroupSummary, BatchExtractionResponse } from '@/types/grouping';

interface BatchExtractionPanelProps {
  groups: GroupSummary[];
}

export function BatchExtractionPanel({ groups }: BatchExtractionPanelProps) {
  const { mutate: runBatch, isLoading } = useRunBatchExtraction();

  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(groups.map((g) => g.group_name)),
  );
  const [dryRun, setDryRun] = useState(true);
  const [stopOnError, setStopOnError] = useState(false);
  const [result, setResult] = useState<BatchExtractionResponse | null>(null);

  const toggleGroup = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === groups.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(groups.map((g) => g.group_name)));
    }
  };

  const handleRunBatch = async () => {
    const res = await runBatch({
      group_names: Array.from(selected),
      dry_run: dryRun,
      stop_on_error: stopOnError,
    });
    if (res) setResult(res);
  };

  const perGroupResults = result ? Object.entries(result.per_group) : [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Batch Extraction
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Group selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-neutral-700">Select Groups</h4>
            <button
              className="text-xs text-blue-600 hover:underline"
              onClick={toggleAll}
            >
              {selected.size === groups.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>
          <div className="border rounded-lg divide-y max-h-48 overflow-y-auto">
            {groups.map((g) => (
              <label
                key={g.group_name}
                className="flex items-center gap-3 px-3 py-2 hover:bg-neutral-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.has(g.group_name)}
                  onChange={() => toggleGroup(g.group_name)}
                  className="rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium flex-1">{g.group_name}</span>
                <span className="text-xs text-neutral-400">{g.file_count} files</span>
              </label>
            ))}
          </div>
        </div>

        {/* Options */}
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
            />
            Dry Run
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={stopOnError}
              onChange={(e) => setStopOnError(e.target.checked)}
              className="rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
            />
            Stop on Error
          </label>
        </div>

        {/* Run button */}
        <Button
          onClick={handleRunBatch}
          disabled={isLoading || selected.size === 0}
          className="w-full"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Zap className="h-4 w-4 mr-2" />
          )}
          Run Batch ({selected.size} group{selected.size !== 1 ? 's' : ''})
          {dryRun && ' - Dry Run'}
        </Button>

        {/* Results */}
        {result && (
          <div className="space-y-3 pt-2 border-t">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg bg-neutral-50 p-2.5 text-center">
                <div className="text-lg font-semibold">{result.groups_processed}</div>
                <div className="text-xs text-neutral-500">Groups</div>
              </div>
              <div className="rounded-lg bg-green-50 p-2.5 text-center">
                <div className="text-lg font-semibold text-green-700">{result.total_files}</div>
                <div className="text-xs text-neutral-500">Files</div>
              </div>
              <div className="rounded-lg bg-blue-50 p-2.5 text-center">
                <div className="text-lg font-semibold text-blue-700">
                  {result.total_values.toLocaleString()}
                </div>
                <div className="text-xs text-neutral-500">Values</div>
              </div>
              <div className="rounded-lg bg-red-50 p-2.5 text-center">
                <div className="text-lg font-semibold text-red-700">{result.groups_failed}</div>
                <div className="text-xs text-neutral-500">Failed</div>
              </div>
            </div>

            {/* Per-group status cards */}
            <div className="space-y-1.5">
              {perGroupResults.map(([name, res]) => {
                const success = res.files_processed - res.files_failed;
                const hasFails = res.files_failed > 0;

                return (
                  <div
                    key={name}
                    className={cn(
                      'flex items-center justify-between px-3 py-2 rounded-lg border text-sm',
                      hasFails ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {hasFails ? (
                        <XCircle className="h-4 w-4 text-amber-500" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      )}
                      <span className="font-medium">{name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-neutral-500">
                        {success}/{res.files_processed} files
                      </span>
                      <Badge variant="secondary" className="text-xs">
                        {res.total_values} values
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
