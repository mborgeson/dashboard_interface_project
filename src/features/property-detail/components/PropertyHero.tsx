import { Building2, MapPin, Calendar, TrendingUp } from 'lucide-react';
import type { Property } from '@/types';
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils/formatters';

interface PropertyHeroProps {
  property: Property;
}

export function PropertyHero({ property }: PropertyHeroProps) {
  const getClassColor = (propertyClass: string) => {
    switch (propertyClass) {
      case 'A':
        return 'bg-primary-100 text-primary-800';
      case 'B':
        return 'bg-accent-100 text-accent-800';
      case 'C':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Property Image */}
        <div className="lg:col-span-1">
          <div className="aspect-[4/3] bg-gray-200 relative">
            {property.images.main ? (
              <img
                src={property.images.main}
                alt={property.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <Building2 className="w-16 h-16 text-gray-400" />
              </div>
            )}
          </div>
        </div>

        {/* Property Info */}
        <div className="lg:col-span-2 p-6 space-y-6">
          {/* Header */}
          <div>
            <div className="flex items-start justify-between mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{property.name}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getClassColor(property.propertyDetails.propertyClass)}`}>
                Class {property.propertyDetails.propertyClass}
              </span>
            </div>
            <div className="flex items-center gap-2 text-gray-600 mb-4">
              <MapPin className="w-4 h-4" />
              <span>
                {property.address.street}, {property.address.city}, {property.address.state} {property.address.zip}
              </span>
              <span className="mx-2">•</span>
              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-sm">
                {property.address.submarket}
              </span>
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Units</div>
              <div className="text-2xl font-bold text-gray-900">{formatNumber(property.propertyDetails.units)}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Square Feet</div>
              <div className="text-2xl font-bold text-gray-900">{formatNumber(property.propertyDetails.squareFeet)}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-1 text-sm text-gray-600 mb-1">
                <Calendar className="w-3 h-3" />
                <span>Year Built</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{property.propertyDetails.yearBuilt}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Asset Type</div>
              <div className="text-2xl font-bold text-gray-900">{property.propertyDetails.assetType}</div>
            </div>
          </div>

          {/* Value & Occupancy */}
          <div className="flex items-center gap-6 pt-4 border-t">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-green-600" />
              <div>
                <div className="text-sm text-gray-600">Current Value</div>
                <div className="text-xl font-bold text-gray-900">{formatCurrency(property.valuation.currentValue)}</div>
              </div>
            </div>
            <div className="h-12 w-px bg-gray-200" />
            <div>
              <div className="text-sm text-gray-600">Occupancy</div>
              <div className="flex items-center gap-2">
                <div className="text-xl font-bold text-gray-900">{formatPercent(property.operations.occupancy)}</div>
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 rounded-full h-2"
                    style={{ width: `${property.operations.occupancy * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
