import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  AlertTriangle, ChevronRight, ChevronDown, Loader2, Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ConflictCheckResponse } from '@/types/grouping';

interface ConflictReportProps {
  conflicts: ConflictCheckResponse | null;
  isLoading: boolean;
}

export function ConflictReport({ conflicts, isLoading }: ConflictReportProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [overrides, setOverrides] = useState<Record<string, 'overwrite' | 'skip'>>({});

  const toggleGroup = (groupName: string) => {
    setExpanded((prev) => ({ ...prev, [groupName]: !prev[groupName] }));
  };

  const toggleOverride = (key: string) => {
    setOverrides((prev) => ({
      ...prev,
      [key]: prev[key] === 'overwrite' ? 'skip' : 'overwrite',
    }));
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400" />
          <p className="text-sm text-neutral-500 mt-2">Running conflict check...</p>
        </CardContent>
      </Card>
    );
  }

  if (!conflicts) return null;

  const groupEntries = Object.entries(conflicts.conflicts ?? {});

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Conflict Report
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={conflicts.total_conflicts > 0 ? 'destructive' : 'secondary'}>
              {conflicts.total_conflicts} conflict{conflicts.total_conflicts !== 1 ? 's' : ''}
            </Badge>
            <Badge variant="outline">
              {conflicts.groups_with_conflicts} group{conflicts.groups_with_conflicts !== 1 ? 's' : ''}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {conflicts.total_conflicts === 0 ? (
          <div className="py-6 text-center">
            <Shield className="h-10 w-10 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-green-700 font-medium">No conflicts found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {groupEntries.map(([groupName, items]) => {
              const conflictList = items as Array<Record<string, unknown>>;
              if (conflictList.length === 0) return null;
              const isOpen = expanded[groupName] ?? false;

              return (
                <div key={groupName} className="border rounded-lg overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 hover:bg-neutral-100 transition-colors"
                    onClick={() => toggleGroup(groupName)}
                  >
                    <div className="flex items-center gap-2">
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4 text-neutral-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-neutral-500" />
                      )}
                      <span className="font-medium text-sm">{groupName}</span>
                    </div>
                    <Badge variant="destructive">{conflictList.length}</Badge>
                  </button>

                  {isOpen && (
                    <div className="divide-y">
                      {conflictList.map((conflict, idx) => {
                        const key = `${groupName}-${idx}`;
                        const action = overrides[key] ?? 'skip';

                        return (
                          <div key={key} className="px-4 py-3 text-sm">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 space-y-1">
                                <div className="flex items-center gap-2">
                                  <AlertTriangle className={cn(
                                    'h-3.5 w-3.5',
                                    conflict.severity === 'high' ? 'text-red-500' :
                                    conflict.severity === 'medium' ? 'text-amber-500' : 'text-neutral-400',
                                  )} />
                                  <span className="font-medium text-neutral-800">
                                    {String(conflict.field ?? 'Unknown field')}
                                  </span>
                                  {conflict.severity ? (
                                    <Badge
                                      variant={conflict.severity === 'high' ? 'destructive' : 'outline'}
                                      className="text-[10px] px-1.5 py-0"
                                    >
                                      {String(conflict.severity)}
                                    </Badge>
                                  ) : null}
                                </div>
                                {conflict.property ? (
                                  <p className="text-xs text-neutral-500">
                                    Property: {String(conflict.property)}
                                  </p>
                                ) : null}
                                <div className="flex items-center gap-3 text-xs">
                                  <span className="text-red-600">
                                    Old: <code className="bg-red-50 px-1 rounded">{String(conflict.old_value ?? '-')}</code>
                                  </span>
                                  <span className="text-neutral-400">&rarr;</span>
                                  <span className="text-green-600">
                                    New: <code className="bg-green-50 px-1 rounded">{String(conflict.new_value ?? '-')}</code>
                                  </span>
                                </div>
                              </div>
                              <button
                                className={cn(
                                  'px-3 py-1 rounded text-xs font-medium border transition-colors',
                                  action === 'overwrite'
                                    ? 'bg-amber-100 border-amber-300 text-amber-800'
                                    : 'bg-neutral-100 border-neutral-300 text-neutral-600',
                                )}
                                onClick={() => toggleOverride(key)}
                              >
                                {action === 'overwrite' ? 'Overwrite' : 'Skip'}
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
