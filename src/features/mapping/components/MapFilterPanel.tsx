import { useState } from 'react';
import { X, Filter, RotateCcw } from 'lucide-react';
import type { PhoenixSubmarket } from '@/types';
import type { MapFilters } from '../hooks/useMapFilters';
import { formatCurrency } from '@/lib/utils/formatters';

interface MapFilterPanelProps {
  filters: MapFilters;
  filteredCount: number;
  totalCount: number;
  valueRange: [number, number];
  onTogglePropertyClass: (propertyClass: 'A' | 'B' | 'C') => void;
  onToggleSubmarket: (submarket: PhoenixSubmarket) => void;
  onValueRangeChange: (range: [number, number]) => void;
  onOccupancyRangeChange: (range: [number, number]) => void;
  onReset: () => void;
}

export function MapFilterPanel({
  filters,
  filteredCount,
  totalCount,
  valueRange,
  onTogglePropertyClass,
  onToggleSubmarket,
  onValueRangeChange,
  onOccupancyRangeChange,
  onReset,
}: MapFilterPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const submarkets: PhoenixSubmarket[] = [
    'Tempe',
    'East Valley',
    'Downtown Phoenix',
    'North Phoenix',
    'Deer Valley',
    'Chandler',
    'Gilbert',
    'Old Town Scottsdale',
    'North West Valley',
    'South West Valley',
    'South Phoenix',
    'North Scottsdale',
    'West Maricopa County',
    'Camelback',
    'Southeast Valley',
  ];

  if (isCollapsed) {
    return (
      <div className="absolute top-4 left-4 z-[1000]">
        <button
          onClick={() => setIsCollapsed(false)}
          className="bg-white rounded-lg shadow-md p-3 hover:bg-neutral-50 transition-colors"
          aria-label="Show filters"
        >
          <Filter className="w-5 h-5 text-neutral-700" />
        </button>
      </div>
    );
  }

  return (
    <div className="absolute top-4 left-4 z-[1000] w-80 bg-white rounded-lg shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-neutral-700" />
          <h2 className="text-lg font-semibold text-neutral-900">Filters</h2>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 hover:bg-neutral-100 rounded transition-colors"
          aria-label="Hide filters"
        >
          <X className="w-5 h-5 text-neutral-500" />
        </button>
      </div>

      {/* Filter Content */}
      <div className="p-4 space-y-6 max-h-[calc(100vh-200px)] overflow-y-auto">
        {/* Property Count */}
        <div className="bg-primary-50 rounded-lg p-3">
          <div className="text-sm text-neutral-600">Showing</div>
          <div className="text-2xl font-bold text-primary-700">
            {filteredCount} <span className="text-sm font-normal">of {totalCount}</span>
          </div>
          <div className="text-sm text-neutral-600">properties</div>
        </div>

        {/* Property Class */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3">Property Class</h3>
          <div className="space-y-2">
            {(['A', 'B', 'C'] as const).map(propertyClass => (
              <label key={propertyClass} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.propertyClasses.has(propertyClass)}
                  onChange={() => onTogglePropertyClass(propertyClass)}
                  className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-neutral-700">Class {propertyClass}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Submarkets */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3">Submarket</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {submarkets.map(submarket => (
              <label key={submarket} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.submarkets.has(submarket)}
                  onChange={() => onToggleSubmarket(submarket)}
                  className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-neutral-700">{submarket}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Value Range */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3">Property Value</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={filters.valueRange[0]}
                onChange={e => onValueRangeChange([Number(e.target.value), filters.valueRange[1]])}
                className="w-full px-3 py-2 text-sm border border-neutral-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Min"
              />
              <span className="text-neutral-500">-</span>
              <input
                type="number"
                value={filters.valueRange[1]}
                onChange={e => onValueRangeChange([filters.valueRange[0], Number(e.target.value)])}
                className="w-full px-3 py-2 text-sm border border-neutral-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Max"
              />
            </div>
            <div className="flex justify-between text-xs text-neutral-600">
              <span>{formatCurrency(valueRange[0], true)}</span>
              <span>{formatCurrency(valueRange[1], true)}</span>
            </div>
          </div>
        </div>

        {/* Occupancy Range */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3">Occupancy (%)</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={filters.occupancyRange[0]}
                onChange={e =>
                  onOccupancyRangeChange([Number(e.target.value), filters.occupancyRange[1]])
                }
                min="0"
                max="100"
                className="w-full px-3 py-2 text-sm border border-neutral-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Min %"
              />
              <span className="text-neutral-500">-</span>
              <input
                type="number"
                value={filters.occupancyRange[1]}
                onChange={e =>
                  onOccupancyRangeChange([filters.occupancyRange[0], Number(e.target.value)])
                }
                min="0"
                max="100"
                className="w-full px-3 py-2 text-sm border border-neutral-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Max %"
              />
            </div>
          </div>
        </div>

        {/* Reset Button */}
        <button
          onClick={onReset}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-lg transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          <span className="text-sm font-medium">Reset Filters</span>
        </button>
      </div>
    </div>
  );
}
