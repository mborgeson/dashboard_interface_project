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
import type { SubmarketPipelineItem } from '../types';

interface SubmarketPipelineProps {
  data: SubmarketPipelineItem[];
  isLoading: boolean;
}

const numFmt = new Intl.NumberFormat('en-US');

export function SubmarketPipeline({ data, isLoading }: SubmarketPipelineProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline by Submarket</CardTitle>
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
        <CardTitle>Pipeline by Submarket</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No data available</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Submarket</TableHead>
                  <TableHead className="text-right">Projects</TableHead>
                  <TableHead className="text-right">Total Units</TableHead>
                  <TableHead className="text-right">Proposed</TableHead>
                  <TableHead className="text-right">Under Constr.</TableHead>
                  <TableHead className="text-right">Delivered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((r) => (
                  <TableRow key={r.submarket}>
                    <TableCell className="font-medium">{r.submarket}</TableCell>
                    <TableCell className="text-right">{r.totalProjects}</TableCell>
                    <TableCell className="text-right">{numFmt.format(r.totalUnits)}</TableCell>
                    <TableCell className="text-right">{r.proposed}</TableCell>
                    <TableCell className="text-right">{r.underConstruction}</TableCell>
                    <TableCell className="text-right">{r.delivered}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
