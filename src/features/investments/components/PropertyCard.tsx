import { Building2, Users, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';
import type { Property } from '@/types';

interface PropertyCardProps {
  property: Property;
  onViewDetails?: (propertyId: string) => void;
}

export function PropertyCard({ property, onViewDetails }: PropertyCardProps) {
  // Property class color mapping
  const classColors = {
    A: 'bg-emerald-500',
    B: 'bg-blue-500',
    C: 'bg-amber-500',
  };

  const classColor = classColors[property.propertyDetails.propertyClass as keyof typeof classColors] || 'bg-gray-500';

  return (
    <Card className="flex h-full flex-col overflow-hidden transition-shadow hover:shadow-lg">
      {/* Image Placeholder */}
      <div className={`${classColor} relative h-48 w-full`}>
        <div className="absolute inset-0 flex items-center justify-center bg-black/10">
          <Building2 className="h-16 w-16 text-white/80" />
        </div>
        {/* Property Class Badge */}
        <div className="absolute right-3 top-3">
          <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-gray-900">
            Class {property.propertyDetails.propertyClass}
          </span>
        </div>
      </div>

      {/* Card Header */}
      <CardHeader className="space-y-1">
        <h3 className="text-lg font-semibold leading-tight">{property.name}</h3>
        <p className="text-sm text-muted-foreground">
          {property.address.street}
          <br />
          {property.address.city}, {property.address.state}
        </p>
        <p className="text-xs text-muted-foreground">{property.address.submarket}</p>
      </CardHeader>

      {/* Card Content */}
      <CardContent className="flex-1 space-y-4">
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          {/* Units */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Users className="h-3 w-3" />
              <span>Units</span>
            </div>
            <p className="text-lg font-semibold">{property.propertyDetails.units}</p>
          </div>

          {/* Occupancy */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Occupancy</p>
            <p className="text-lg font-semibold">{formatPercent(property.operations.occupancy)}</p>
          </div>

          {/* NOI */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">NOI</p>
            <p className="text-sm font-semibold">{formatCurrency(property.operations.noi, true)}</p>
          </div>

          {/* Cap Rate */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Cap Rate</p>
            <p className="text-sm font-semibold">{formatPercent(property.valuation.capRate)}</p>
          </div>

          {/* IRR */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3" />
              <span>IRR</span>
            </div>
            <p className="text-sm font-semibold text-green-600">
              {formatPercent(property.performance.leveredIrr)}
            </p>
          </div>

          {/* Value */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Value</p>
            <p className="text-sm font-semibold">{formatCurrency(property.valuation.currentValue, true)}</p>
          </div>
        </div>
      </CardContent>

      {/* Card Footer */}
      <CardFooter className="pt-0">
        <Button 
          variant="outline" 
          className="w-full"
          onClick={() => onViewDetails?.(property.id)}
        >
          View Details
        </Button>
      </CardFooter>
    </Card>
  );
}
