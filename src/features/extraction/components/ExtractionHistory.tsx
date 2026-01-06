import { useState } from 'react';
import { useExtractionHistory, getExtractionDuration } from '../hooks/useExtraction';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { TableSkeleton } from '@/components/skeletons';
import {
  History,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Square,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Clock,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExtractionRun, ExtractionStatus } from '@/types/extraction';

interface ExtractionHistoryProps {
  onRunClick?: (run: ExtractionRun) => void;
  limit?: number;
  className?: string;
}

function getStatusIcon(status: ExtractionStatus) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-600" />;
    case 'cancelled':
      return <Square className="h-4 w-4 text-neutral-500" />;
  }
}

function getStatusBadgeVariant(status: ExtractionStatus) {
  switch (status) {
    case 'running':
      return 'default' as const;
    case 'completed':
      return 'secondary' as const;
    case 'failed':
      return 'destructive' as const;
    case 'cancelled':
      return 'outline' as const;
  }
}

export function ExtractionHistory({
  onRunClick,
  limit = 10,
  className,
}: ExtractionHistoryProps) {
  const [page, setPage] = useState(1);
  const { runs, total, pageSize, isLoading, error, refetch } = useExtractionHistory(limit, page);

  const totalPages = Math.ceil(total / pageSize);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5" />
            Extraction History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <TableSkeleton rows={5} columns={6} />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5" />
            Extraction History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
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

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5" />
            Extraction History
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={refetch}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <History className="h-10 w-10 text-neutral-300 mb-2" />
            <p className="text-sm text-neutral-600">No extraction runs found</p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Files</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead className="text-right">Success Rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => {
                  const successRate =
                    run.files_processed > 0
                      ? ((run.files_processed - run.files_failed) / run.files_processed) * 100
                      : 0;

                  return (
                    <TableRow
                      key={run.id}
                      className={cn(
                        "cursor-pointer",
                        onRunClick && "hover:bg-neutral-50"
                      )}
                      onClick={() => onRunClick?.(run)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(run.status)}
                          <Badge variant={getStatusBadgeVariant(run.status)}>
                            {run.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <Calendar className="h-3 w-3 text-neutral-400" />
                          {new Date(run.started_at).toLocaleDateString()}
                          <span className="text-neutral-400 mx-1">at</span>
                          {new Date(run.started_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <Clock className="h-3 w-3 text-neutral-400" />
                          {getExtractionDuration(run)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <span className="text-green-600 font-medium">
                            {run.files_processed - run.files_failed}
                          </span>
                          <span className="text-neutral-400"> / </span>
                          <span>{run.files_discovered}</span>
                          {run.files_failed > 0 && (
                            <span className="text-red-600 ml-1">
                              ({run.files_failed} failed)
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <User className="h-3 w-3 text-neutral-400" />
                          <span className="capitalize">{run.trigger_type}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={cn(
                            "font-medium",
                            successRate >= 90
                              ? "text-green-600"
                              : successRate >= 70
                              ? "text-amber-600"
                              : "text-red-600"
                          )}
                        >
                          {successRate.toFixed(0)}%
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-neutral-500">
                  Showing {(page - 1) * pageSize + 1} to{' '}
                  {Math.min(page * pageSize, total)} of {total} runs
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
