import { useState } from 'react';
import { useGroups, useRunGroupExtraction, useApproveGroup } from '../hooks/useGroupPipeline';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Loader2, Eye, CheckCircle, Play, ArrowUpDown, Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GroupSummary } from '@/types/grouping';

interface GroupListProps {
  onGroupSelect: (name: string) => void;
}

type SortField = 'group_name' | 'file_count' | 'era' | 'structural_overlap' | 'sub_variant_count';
type SortDir = 'asc' | 'desc';

function sortGroups(groups: GroupSummary[], field: SortField, dir: SortDir): GroupSummary[] {
  return [...groups].sort((a, b) => {
    const aVal = a[field];
    const bVal = b[field];
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return dir === 'asc' ? aVal - bVal : bVal - aVal;
    }
    const aStr = String(aVal);
    const bStr = String(bVal);
    return dir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });
}

export function GroupList({ onGroupSelect }: GroupListProps) {
  const { groups, totalGroups, totalUngrouped, isLoading, error, refetch } = useGroups();
  const { mutate: runExtraction, isLoading: extracting } = useRunGroupExtraction();
  const { mutate: approveGroup, isLoading: approving } = useApproveGroup();

  const [sortField, setSortField] = useState<SortField>('group_name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const handleDryRun = async (name: string) => {
    setActiveAction(`dryrun-${name}`);
    await runExtraction(name, { dry_run: true });
    setActiveAction(null);
    refetch();
  };

  const handleApprove = async (name: string) => {
    setActiveAction(`approve-${name}`);
    await approveGroup(name);
    setActiveAction(null);
    refetch();
  };

  const handleExtract = async (name: string) => {
    setActiveAction(`extract-${name}`);
    await runExtraction(name, { dry_run: false });
    setActiveAction(null);
    refetch();
  };

  const sorted = sortGroups(groups, sortField, sortDir);

  const SortBtn = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <button className="flex items-center gap-1 hover:text-neutral-900" onClick={() => toggleSort(field)}>
      {children}
      <ArrowUpDown className={cn('h-3 w-3', sortField === field ? 'text-blue-600' : 'text-neutral-400')} />
    </button>
  );

  const ActionBtn = ({ action, name, icon, label, variant = 'outline' as const, handler }: {
    action: string; name: string; icon: React.ReactNode; label?: string;
    variant?: 'outline' | 'default' | 'ghost'; handler: (n: string) => void;
  }) => (
    <Button variant={variant} size="sm" onClick={() => handler(name)}
      disabled={extracting || approving || activeAction === `${action}-${name}`} title={action}>
      {activeAction === `${action}-${name}` ? <Loader2 className="h-3 w-3 animate-spin" /> : icon}
      {label && ` ${label}`}
    </Button>
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-sm text-red-600 mb-2">{error.message}</p>
          <Button variant="outline" size="sm" onClick={refetch}>Retry</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Layers className="h-5 w-5" />
            File Groups
          </CardTitle>
          <div className="flex items-center gap-3 text-sm text-neutral-500">
            <span>{totalGroups} groups</span>
            {totalUngrouped > 0 && (
              <Badge variant="outline">{totalUngrouped} ungrouped</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {groups.length === 0 ? (
          <div className="py-8 text-center">
            <Layers className="h-10 w-10 text-neutral-300 mx-auto mb-2" />
            <p className="text-sm text-neutral-600">No groups yet. Run Discovery & Fingerprint first.</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead><SortBtn field="group_name">Group Name</SortBtn></TableHead>
                <TableHead><SortBtn field="file_count">Files</SortBtn></TableHead>
                <TableHead><SortBtn field="era">Era</SortBtn></TableHead>
                <TableHead><SortBtn field="structural_overlap">Overlap</SortBtn></TableHead>
                <TableHead><SortBtn field="sub_variant_count">Sub-variants</SortBtn></TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((g) => (
                <TableRow key={g.group_name} className="cursor-pointer hover:bg-neutral-50">
                  <TableCell>
                    <button
                      className="text-blue-600 hover:underline font-medium text-left"
                      onClick={() => onGroupSelect(g.group_name)}
                    >
                      {g.group_name}
                    </button>
                  </TableCell>
                  <TableCell>{g.file_count}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{g.era}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      'font-medium',
                      g.structural_overlap >= 90 ? 'text-green-600' :
                      g.structural_overlap >= 70 ? 'text-amber-600' : 'text-red-600'
                    )}>
                      {g.structural_overlap.toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell>{g.sub_variant_count}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => onGroupSelect(g.group_name)} title="View">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <ActionBtn action="dryrun" name={g.group_name} icon={<Play className="h-3 w-3" />} handler={handleDryRun} />
                      <ActionBtn action="approve" name={g.group_name} icon={<CheckCircle className="h-3 w-3" />} handler={handleApprove} />
                      <ActionBtn action="extract" name={g.group_name} icon={null} label="Extract" variant="default" handler={handleExtract} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
