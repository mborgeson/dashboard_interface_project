import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { ProjectRecord } from '../types';

interface PipelineTableProps {
  data: ProjectRecord[];
  isLoading: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  final_planning: 'Final Planning',
  permitted: 'Permitted',
  under_construction: 'Under Construction',
  delivered: 'Delivered',
};

const STATUS_COLORS: Record<string, string> = {
  proposed: 'bg-gray-100 text-gray-800',
  final_planning: 'bg-yellow-100 text-yellow-800',
  permitted: 'bg-orange-100 text-orange-800',
  under_construction: 'bg-red-100 text-red-800',
  delivered: 'bg-green-100 text-green-800',
};

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="text-muted-foreground">--</span>;
  const label = STATUS_LABELS[status] ?? status;
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}

const numFmt = new Intl.NumberFormat('en-US');

export function PipelineTable({ data, isLoading }: PipelineTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Construction Projects</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Construction Projects</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project Name</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Submarket</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Units</TableHead>
                <TableHead>Developer</TableHead>
                <TableHead>Rent Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    No projects found
                  </TableCell>
                </TableRow>
              ) : (
                data.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium max-w-[200px] truncate">
                      {r.projectName ?? '--'}
                    </TableCell>
                    <TableCell>{r.city ?? '--'}</TableCell>
                    <TableCell>{r.submarketCluster ?? '--'}</TableCell>
                    <TableCell>
                      <StatusBadge status={r.pipelineStatus} />
                    </TableCell>
                    <TableCell>{r.primaryClassification ?? '--'}</TableCell>
                    <TableCell className="text-right">
                      {r.numberOfUnits ? numFmt.format(r.numberOfUnits) : '--'}
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate">
                      {r.developerName ?? '--'}
                    </TableCell>
                    <TableCell>{r.rentType ?? '--'}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
