import { useGroupDetail, useRunGroupExtraction, useApproveGroup } from '../hooks/useGroupPipeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  X, Loader2, Play, CheckCircle, Download, FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface GroupDetailProps {
  groupName: string;
  onClose: () => void;
}

export function GroupDetail({ groupName, onClose }: GroupDetailProps) {
  const { detail, isLoading, error, refetch } = useGroupDetail(groupName);
  const { mutate: runExtraction, isLoading: extracting } = useRunGroupExtraction();
  const { mutate: approveGroup, isLoading: approving } = useApproveGroup();

  const handleDryRun = async () => {
    await runExtraction(groupName, { dry_run: true });
    refetch();
  };

  const handleApprove = async () => {
    await approveGroup(groupName);
    refetch();
  };

  const handleExtract = async () => {
    await runExtraction(groupName, { dry_run: false });
    refetch();
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400" />
        </CardContent>
      </Card>
    );
  }

  if (error || !detail) {
    return (
      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-sm text-red-600 mb-2">{error?.message ?? 'Group not found'}</p>
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
            <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const varianceEntries = Object.entries(detail.variances ?? {});

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {detail.group_name}
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg bg-neutral-50 p-3 text-center">
            <div className="text-lg font-semibold text-neutral-900">
              {detail.files.length}
            </div>
            <div className="text-xs text-neutral-500">Files</div>
          </div>
          <div className="rounded-lg bg-neutral-50 p-3 text-center">
            <div className="text-lg font-semibold text-neutral-900">
              <Badge variant="secondary">{detail.era}</Badge>
            </div>
            <div className="text-xs text-neutral-500 mt-1">Era</div>
          </div>
          <div className="rounded-lg bg-neutral-50 p-3 text-center">
            <div className={cn(
              'text-lg font-semibold',
              detail.structural_overlap >= 90 ? 'text-green-600' :
              detail.structural_overlap >= 70 ? 'text-amber-600' : 'text-red-600',
            )}>
              {detail.structural_overlap.toFixed(1)}%
            </div>
            <div className="text-xs text-neutral-500">Overlap</div>
          </div>
          <div className="rounded-lg bg-neutral-50 p-3 text-center">
            <div className="text-lg font-semibold text-neutral-900">
              {detail.sub_variants.length}
            </div>
            <div className="text-xs text-neutral-500">Sub-variants</div>
          </div>
        </div>

        {/* Sub-variants list */}
        {detail.sub_variants.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-neutral-700 mb-1.5">Sub-variants</h4>
            <div className="flex flex-wrap gap-1.5">
              {detail.sub_variants.map((sv) => (
                <Badge key={sv} variant="outline">{sv}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Files table */}
        <div>
          <h4 className="text-sm font-medium text-neutral-700 mb-1.5">Files</h4>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File Path</TableHead>
                  <TableHead>Deal Name</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.files.map((file, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="text-xs font-mono truncate max-w-[300px]" title={String(file.path ?? '')}>
                      {String(file.path ?? file.file_path ?? '-')}
                    </TableCell>
                    <TableCell className="text-sm">
                      {String(file.deal_name ?? file.name ?? '-')}
                    </TableCell>
                    <TableCell>
                      <Badge variant={file.status === 'extracted' ? 'secondary' : 'outline'}>
                        {String(file.status ?? 'pending')}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Variances */}
        {varianceEntries.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-amber-700 mb-1.5">Variances</h4>
            <div className="border border-amber-200 rounded-lg bg-amber-50 p-3 space-y-2">
              {varianceEntries.map(([key, val]) => (
                <div key={key} className="flex items-start gap-2 text-sm">
                  <span className="font-medium text-amber-800 min-w-[120px]">{key}:</span>
                  <span className="text-amber-700">{JSON.stringify(val)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 pt-2 border-t">
          <Button variant="outline" size="sm" onClick={handleDryRun} disabled={extracting}>
            {extracting ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Play className="h-4 w-4 mr-1.5" />}
            Dry Run
          </Button>
          <Button variant="outline" size="sm" onClick={handleApprove} disabled={approving}>
            {approving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-1.5" />}
            Approve
          </Button>
          <Button size="sm" onClick={handleExtract} disabled={extracting}>
            {extracting ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Download className="h-4 w-4 mr-1.5" />}
            Extract (Live)
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
