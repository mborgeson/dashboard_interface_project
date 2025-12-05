import { useState } from 'react';
import { Card } from '@/components/ui/card';
import type { SubmarketMetrics } from '@/types/market';

interface MarketHeatmapProps {
  submarkets: Array<SubmarketMetrics & { rentGrowthPct: number; occupancyPct: number; capRatePct: number }>;
}

type HeatmapMetric = 'rentGrowth' | 'occupancy' | 'capRate';

export function MarketHeatmap({ submarkets }: MarketHeatmapProps) {
  const [selectedMetric, setSelectedMetric] = useState<HeatmapMetric>('rentGrowth');

  const metrics = [
    { key: 'rentGrowth' as HeatmapMetric, label: 'Rent Growth', format: (v: number) => `${v.toFixed(1)}%`, reverse: false },
    { key: 'occupancy' as HeatmapMetric, label: 'Occupancy', format: (v: number) => `${v.toFixed(1)}%`, reverse: false },
    { key: 'capRate' as HeatmapMetric, label: 'Cap Rate', format: (v: number) => `${v.toFixed(2)}%`, reverse: true },
  ];

  const currentMetric = metrics.find(m => m.key === selectedMetric) || metrics[0];

  // Get values for the selected metric
  const values = submarkets.map(s =>
    selectedMetric === 'rentGrowth' ? s.rentGrowthPct :
    selectedMetric === 'occupancy' ? s.occupancyPct :
    s.capRatePct
  );

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  // Get color based on value (normalized 0-1)
  const getColor = (value: number) => {
    const normalized = (value - minValue) / (maxValue - minValue);
    // Reverse color scale for cap rate (lower is better)
    const intensity = currentMetric.reverse ? 1 - normalized : normalized;

    // Color scale: red (low) -> yellow (mid) -> green (high)
    if (intensity < 0.33) {
      return `rgb(${Math.round(239 + intensity * 3 * 16)}, ${Math.round(68 + intensity * 3 * 116)}, ${Math.round(68 + intensity * 3 * 61)})`;
    } else if (intensity < 0.67) {
      const localIntensity = (intensity - 0.33) / 0.34;
      return `rgb(${Math.round(251 - localIntensity * 62)}, ${Math.round(191 - localIntensity * 8)}, ${Math.round(36 + localIntensity * 93)})`;
    } else {
      const localIntensity = (intensity - 0.67) / 0.33;
      return `rgb(${Math.round(16 + localIntensity * 1)}, ${Math.round(185 - localIntensity * 55)}, ${Math.round(129 - localIntensity * 21)})`;
    }
  };

  // Get text color based on background
  const getTextColor = (value: number) => {
    const normalized = (value - minValue) / (maxValue - minValue);
    const intensity = currentMetric.reverse ? 1 - normalized : normalized;
    return intensity > 0.5 ? 'text-white' : 'text-neutral-900';
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-card-title text-primary-500">Market Performance Heatmap</h3>
        <div className="flex gap-2">
          {metrics.map(metric => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === metric.key
                  ? 'bg-primary-500 text-white'
                  : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
              }`}
            >
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {submarkets.map(submarket => {
          const value = selectedMetric === 'rentGrowth' ? submarket.rentGrowthPct :
                       selectedMetric === 'occupancy' ? submarket.occupancyPct :
                       submarket.capRatePct;

          const bgColor = getColor(value);
          const textColor = getTextColor(value);

          return (
            <div
              key={submarket.name}
              className="rounded-lg p-4 transition-all duration-300 hover:scale-105 hover:shadow-lg cursor-pointer"
              style={{ backgroundColor: bgColor }}
            >
              <div className={`space-y-2 ${textColor}`}>
                <p className="font-semibold text-sm">{submarket.name}</p>
                <p className="text-2xl font-bold">{currentMetric.format(value)}</p>
                <div className="text-xs opacity-90 space-y-1">
                  <div className="flex justify-between">
                    <span>Avg Rent:</span>
                    <span className="font-medium">${submarket.avgRent.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Inventory:</span>
                    <span className="font-medium">{(submarket.inventory / 1000).toFixed(1)}K</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="text-neutral-600">Performance:</span>
          <div className="flex items-center gap-1">
            <div className="w-12 h-4 rounded" style={{ background: 'linear-gradient(to right, #ef4444, #fbbf24, #10b981)' }}></div>
            <span className="text-neutral-500 text-xs ml-2">
              {currentMetric.reverse ? 'High → Low' : 'Low → High'}
            </span>
          </div>
        </div>
        <span className="text-neutral-500">
          {currentMetric.label} • Phoenix MSA Submarkets
        </span>
      </div>
    </Card>
  );
}
