import { X, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Property } from '@/types';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';

interface PropertyDetailPanelProps {
  property: Property;
  onClose: () => void;
}

export function PropertyDetailPanel({ property, onClose }: PropertyDetailPanelProps) {
  return (
    <div className="absolute top-4 right-4 z-[1000] w-96 bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="relative">
        {/* Property Image Placeholder */}
        <div className="h-48 bg-gradient-to-br from-primary-400 to-primary-600 rounded-t-lg" />
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-2 bg-white rounded-full shadow-md hover:bg-neutral-50 transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5 text-neutral-700" />
        </button>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Property Info */}
        <div>
          <h2 className="text-xl font-bold text-neutral-900 mb-1">{property.name}</h2>
          <p className="text-sm text-neutral-600">
            {property.address.street}
            <br />
            {property.address.city}, {property.address.state} {property.address.zip}
          </p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-neutral-50 rounded-lg p-3">
            <div className="text-xs text-neutral-600 mb-1">Units</div>
            <div className="text-lg font-semibold text-neutral-900">
              {property.propertyDetails.units}
            </div>
          </div>
          <div className="bg-neutral-50 rounded-lg p-3">
            <div className="text-xs text-neutral-600 mb-1">Class</div>
            <div className="text-lg font-semibold text-neutral-900">
              {property.propertyDetails.propertyClass}
            </div>
          </div>
          <div className="bg-neutral-50 rounded-lg p-3">
            <div className="text-xs text-neutral-600 mb-1">Built</div>
            <div className="text-lg font-semibold text-neutral-900">
              {property.propertyDetails.yearBuilt}
            </div>
          </div>
        </div>

        {/* Financial Metrics */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">Property Value</span>
            <span className="text-sm font-semibold text-neutral-900">
              {formatCurrency(property.valuation.currentValue, true)}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">NOI</span>
            <span className="text-sm font-semibold text-neutral-900">
              {formatCurrency(property.operations.noi, true)}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">Cap Rate</span>
            <span className="text-sm font-semibold text-neutral-900">
              {formatPercent(property.valuation.capRate)}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-600">IRR</span>
            <span className="text-sm font-semibold text-primary-700">
              {formatPercent(property.performance.leveredIrr)}
            </span>
          </div>
        </div>

        {/* Occupancy */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-neutral-600">Occupancy</span>
            <span className="text-sm font-semibold text-neutral-900">
              {formatPercent(property.operations.occupancy)}
            </span>
          </div>
          <div className="w-full bg-neutral-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all"
              style={{ width: `${property.operations.occupancy * 100}%` }}
            />
          </div>
        </div>

        {/* View Details Button */}
        <Link
          to="/investments"
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
        >
          <span className="font-medium">View Full Details</span>
          <ExternalLink className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
