import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartSkeleton } from '@/components/ui/skeleton';
import type { SubmarketComparisonRow } from '../types';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

interface SubmarketComparisonProps {
  data: SubmarketComparisonRow[];
  isLoading: boolean;
}

/** Compute color intensity based on value relative to min/max */
function getHeatColor(value: number, min: number, max: number): string {
  if (max === min) return 'bg-blue-200';
  const ratio = (value - min) / (max - min);
  if (ratio < 0.2) return 'bg-blue-100 text-blue-900';
  if (ratio < 0.4) return 'bg-blue-200 text-blue-900';
  if (ratio < 0.6) return 'bg-blue-300 text-blue-900';
  if (ratio < 0.8) return 'bg-blue-500 text-white';
  return 'bg-blue-700 text-white';
}

export function SubmarketComparison({
  data,
  isLoading,
}: SubmarketComparisonProps) {
  const [sortBy, setSortBy] = useState<'volume' | 'price'>('volume');

  const { years, submarketData, minPrice, maxPrice } = useMemo(() => {
    const yearSet = new Set<number>();
    const bySubmarket = new Map<
      string,
      { totalVolume: number; totalCount: number; byYear: Map<number, SubmarketComparisonRow> }
    >();

    for (const row of data) {
      yearSet.add(row.year);
      if (!bySubmarket.has(row.submarket)) {
        bySubmarket.set(row.submarket, {
          totalVolume: 0,
          totalCount: 0,
          byYear: new Map(),
        });
      }
      const entry = bySubmarket.get(row.submarket)!;
      entry.totalVolume += row.totalVolume;
      entry.totalCount += row.salesCount;
      entry.byYear.set(row.year, row);
    }

    const sortedYears = Array.from(yearSet).sort((a, b) => a - b);
    const allPrices = data
      .map((d) => d.avgPricePerUnit)
      .filter((p): p is number => p != null && p > 0);
    const min = allPrices.length > 0 ? Math.min(...allPrices) : 0;
    const max = allPrices.length > 0 ? Math.max(...allPrices) : 1;

    // Sort submarkets
    const sorted = Array.from(bySubmarket.entries()).sort((a, b) => {
      if (sortBy === 'volume') return b[1].totalVolume - a[1].totalVolume;
      // Sort by latest year median price
      const latestYear = sortedYears[sortedYears.length - 1];
      const aPrice = a[1].byYear.get(latestYear)?.avgPricePerUnit ?? 0;
      const bPrice = b[1].byYear.get(latestYear)?.avgPricePerUnit ?? 0;
      return bPrice - aPrice;
    });

    return {
      years: sortedYears,
      submarketData: sorted.slice(0, 20), // Top 20 submarkets
      minPrice: min,
      maxPrice: max,
    };
  }, [data, sortBy]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Submarket Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Submarket Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No submarket data available for the current filters.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Submarket Comparison</CardTitle>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setSortBy('volume')}
            className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
              sortBy === 'volume'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-neutral-700 border-neutral-300 hover:border-blue-400'
            }`}
          >
            By Volume
          </button>
          <button
            type="button"
            onClick={() => setSortBy('price')}
            className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
              sortBy === 'price'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-neutral-700 border-neutral-300 hover:border-blue-400'
            }`}
          >
            By Price
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground mb-3">
          Average price per unit by submarket and year. Top 20 submarkets shown.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-2 font-medium text-muted-foreground sticky left-0 bg-white min-w-[160px]">
                  Submarket
                </th>
                <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                  Sales
                </th>
                {years.map((year) => (
                  <th
                    key={year}
                    className="text-center py-2 px-1 font-medium text-muted-foreground min-w-[80px]"
                  >
                    {year}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {submarketData.map(([submarket, info]) => (
                <tr key={submarket} className="border-b last:border-b-0">
                  <td className="py-1.5 px-2 font-medium truncate max-w-[200px] sticky left-0 bg-white">
                    {submarket}
                  </td>
                  <td className="py-1.5 px-2 text-right text-muted-foreground">
                    {info.totalCount.toLocaleString()}
                  </td>
                  {years.map((year) => {
                    const cell = info.byYear.get(year);
                    if (!cell || cell.avgPricePerUnit === 0) {
                      return (
                        <td
                          key={year}
                          className="py-1.5 px-1 text-center text-muted-foreground"
                        >
                          --
                        </td>
                      );
                    }
                    return (
                      <td key={year} className="py-1 px-1">
                        <div
                          className={`rounded px-1.5 py-0.5 text-center text-[10px] font-medium ${getHeatColor(
                            cell.avgPricePerUnit ?? 0,
                            minPrice,
                            maxPrice
                          )}`}
                          title={`${currencyFormatter.format(cell.avgPricePerUnit ?? 0)} (${cell.salesCount} sales)`}
                        >
                          {currencyFormatter.format(cell.avgPricePerUnit ?? 0)}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
