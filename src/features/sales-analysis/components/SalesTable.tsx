import { useState, useMemo } from 'react';
import { format, parseISO } from 'date-fns';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
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
import type { SaleRecord } from '../types';

interface SalesTableProps {
  data: SaleRecord[];
  isLoading: boolean;
}

type SortDir = 'asc' | 'desc';

interface SortState {
  column: string | null;
  direction: SortDir;
}

interface ColumnDef {
  key: string;
  label: string;
  sortable: boolean;
  align: 'left' | 'right';
  format: (record: SaleRecord) => string;
  width?: string;
}

// Formatters
const currencyFmt = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const currencyFmt2 = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFmt = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0,
});

const coordFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

function formatDate(value: string | null): string {
  if (!value) return '--';
  try {
    return format(parseISO(value), 'MM/dd/yyyy');
  } catch {
    return '--';
  }
}

function fmtNullNum(value: number | null, formatter: Intl.NumberFormat): string {
  return value != null ? formatter.format(value) : '--';
}

const columns: ColumnDef[] = [
  {
    key: 'propertyName',
    label: 'Property Name',
    sortable: true,
    align: 'left',
    format: (r) => r.propertyName ?? '--',
    width: 'min-w-[180px]',
  },
  {
    key: 'propertyCity',
    label: 'City',
    sortable: true,
    align: 'left',
    format: (r) => r.propertyCity ?? '--',
  },
  {
    key: 'submarketCluster',
    label: 'Submarket',
    sortable: true,
    align: 'left',
    format: (r) => r.submarketCluster ?? '--',
  },
  {
    key: 'starRating',
    label: 'Star Rating',
    sortable: true,
    align: 'left',
    format: (r) => r.starRating ?? '--',
  },
  {
    key: 'yearBuilt',
    label: 'Year Built',
    sortable: true,
    align: 'right',
    format: (r) => (r.yearBuilt != null ? String(r.yearBuilt) : '--'),
  },
  {
    key: 'numberOfUnits',
    label: '# Units',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.numberOfUnits, numberFmt),
  },
  {
    key: 'avgUnitSf',
    label: 'Avg Unit SF',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.avgUnitSf, numberFmt),
  },
  {
    key: 'nrsf',
    label: 'NRSF',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.nrsf, numberFmt),
  },
  {
    key: 'saleDate',
    label: 'Sale Date',
    sortable: true,
    align: 'left',
    format: (r) => formatDate(r.saleDate),
  },
  {
    key: 'salePrice',
    label: 'Sale Price',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.salePrice, currencyFmt),
  },
  {
    key: 'pricePerUnit',
    label: 'Price/Unit',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.pricePerUnit, currencyFmt),
  },
  {
    key: 'pricePerNrsf',
    label: 'Price/NRSF',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.pricePerNrsf, currencyFmt2),
  },
  {
    key: 'buyerTrueCompany',
    label: 'Current Owner',
    sortable: true,
    align: 'left',
    format: (r) => r.buyerTrueCompany ?? '--',
    width: 'min-w-[180px]',
  },
  {
    key: 'latitude',
    label: 'Lat',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.latitude, coordFmt),
  },
  {
    key: 'longitude',
    label: 'Lng',
    sortable: true,
    align: 'right',
    format: (r) => fmtNullNum(r.longitude, coordFmt),
  },
];

function getSortValue(record: SaleRecord, key: string): string | number | null {
  const value = record[key as keyof SaleRecord];
  if (value === null || value === undefined) return null;
  return value as string | number;
}

function SortIcon({ column, sort }: { column: string; sort: SortState }) {
  if (sort.column !== column) {
    return <ArrowUpDown className="ml-1 h-3 w-3 opacity-40" />;
  }
  return sort.direction === 'asc' ? (
    <ArrowUp className="ml-1 h-3 w-3" />
  ) : (
    <ArrowDown className="ml-1 h-3 w-3" />
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <TableRow key={i}>
          {columns.map((col) => (
            <TableCell key={col.key}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export function SalesTable({ data, isLoading }: SalesTableProps) {
  const [sort, setSort] = useState<SortState>({ column: null, direction: 'asc' });

  const handleSort = (columnKey: string) => {
    setSort((prev) => {
      if (prev.column === columnKey) {
        return { column: columnKey, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { column: columnKey, direction: 'asc' };
    });
  };

  const sortedData = useMemo(() => {
    if (!sort.column) return data;

    return [...data].sort((a, b) => {
      const aVal = getSortValue(a, sort.column!);
      const bVal = getSortValue(b, sort.column!);

      // Nulls always sort last
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;

      let cmp: number;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else {
        cmp = (aVal as number) - (bVal as number);
      }

      return sort.direction === 'asc' ? cmp : -cmp;
    });
  }, [data, sort.column, sort.direction]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          Sales Data
          {!isLoading && (
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {data.length} records
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((col) => (
                  <TableHead
                    key={col.key}
                    className={`whitespace-nowrap ${col.width ?? ''} ${
                      col.align === 'right' ? 'text-right' : 'text-left'
                    } ${col.sortable ? 'cursor-pointer select-none hover:bg-muted/50' : ''}`}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  >
                    <span className="inline-flex items-center">
                      {col.label}
                      {col.sortable && <SortIcon column={col.key} sort={sort} />}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <SkeletonRows count={10} />
              ) : sortedData.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-32 text-center">
                    <p className="text-muted-foreground">
                      No sales data matches your filters.
                    </p>
                  </TableCell>
                </TableRow>
              ) : (
                sortedData.map((record) => (
                  <TableRow key={record.id}>
                    {columns.map((col) => (
                      <TableCell
                        key={col.key}
                        className={`whitespace-nowrap ${
                          col.align === 'right' ? 'text-right tabular-nums' : 'text-left'
                        }`}
                      >
                        {col.format(record)}
                      </TableCell>
                    ))}
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
