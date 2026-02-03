import { DollarSign, TrendingUp, Percent, Users } from 'lucide-react';
import type { Property } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils/formatters';

interface OverviewTabProps {
  property: Property;
}

export function OverviewTab({ property }: OverviewTabProps) {
  return (
    <div className="p-6 space-y-6">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Current Value</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(property.valuation.currentValue)}</div>
            <p className="text-xs text-green-600 mt-1">
              +{formatPercent(property.valuation.appreciationSinceAcquisition)} since acquisition
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Annual NOI</CardTitle>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(property.operations.noi)}</div>
            <p className="text-xs text-gray-600 mt-1">
              {formatCurrency(property.operations.noi / 12)}/month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Cap Rate</CardTitle>
            <Percent className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercent(property.valuation.capRate)}</div>
            <p className="text-xs text-gray-600 mt-1">Market cap rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">T12 Occupancy</CardTitle>
            <Users className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercent(property.operations.occupancy)}</div>
            <p className="text-xs text-gray-600 mt-1">
              {Math.round(property.propertyDetails.units * property.operations.occupancy)} of {property.propertyDetails.units} units occupied
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Property Details */}
      <Card>
        <CardHeader>
          <CardTitle>Property Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-1">Total Units</div>
              <div className="text-lg font-semibold">{formatNumber(property.propertyDetails.units)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Total Square Feet</div>
              <div className="text-lg font-semibold">{formatNumber(property.propertyDetails.squareFeet)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Average Unit Size</div>
              <div className="text-lg font-semibold">{formatNumber(property.propertyDetails.averageUnitSize)} sq ft</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Year Built</div>
              <div className="text-lg font-semibold">{property.propertyDetails.yearBuilt}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Property Class</div>
              <div className="text-lg font-semibold">Class {property.propertyDetails.propertyClass}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Asset Type</div>
              <div className="text-lg font-semibold">{property.propertyDetails.assetType}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Amenities */}
      <Card>
        <CardHeader>
          <CardTitle>Amenities</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {property.propertyDetails.amenities.map((amenity) => (
              <div key={amenity} className="flex items-center gap-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full" />
                <span className="text-sm text-gray-700">{amenity}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <CardTitle>Location</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Address</span>
              <span className="text-sm font-medium">
                {property.address.street}, {property.address.city}, {property.address.state} {property.address.zip}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Submarket</span>
              <span className="text-sm font-medium">{property.address.submarket}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Coordinates</span>
              <span className="text-sm font-medium">
                {property.address.latitude.toFixed(4)}, {property.address.longitude.toFixed(4)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
