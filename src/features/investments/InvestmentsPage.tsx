import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Grid3x3, List } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { mockProperties } from '@/data/mockProperties';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';
import { PropertyFilters } from './components/PropertyFilters';
import { PropertyCard } from './components/PropertyCard';
import { PropertyTable } from './components/PropertyTable';
import { PropertyCardSkeletonGrid } from '@/components/skeletons';
import { EmptyInvestments } from '@/components/ui/empty-state';

type ViewMode = 'grid' | 'table';
type SortColumn = 'name' | 'submarket' | 'class' | 'units' | 'occupancy' | 'noi' | 'value' | 'irr';

export function InvestmentsPage() {
  const navigate = useNavigate();
  
  // Loading state
  const [isLoading, setIsLoading] = useState(true);
  
  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [propertyClass, setPropertyClass] = useState('all');
  const [submarket, setSubmarket] = useState('all');
  const [occupancyRange, setOccupancyRange] = useState('all');
  const [sortBy, setSortBy] = useState('value-desc');
  
  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  
  // Table sorting state
  const [tableSortColumn, setTableSortColumn] = useState<SortColumn>('value');
  const [tableSortDirection, setTableSortDirection] = useState<'asc' | 'desc'>('desc');

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    const totalProperties = mockProperties.length;
    const totalUnits = mockProperties.reduce((sum, p) => sum + p.propertyDetails.units, 0);
    const totalValue = mockProperties.reduce((sum, p) => sum + p.valuation.currentValue, 0);
    const avgOccupancy = mockProperties.reduce((sum, p) => sum + p.operations.occupancy, 0) / totalProperties;

    return {
      totalProperties,
      totalUnits,
      totalValue,
      avgOccupancy,
    };
  }, []);

  // Filter and sort properties
  const filteredAndSortedProperties = useMemo(() => {
    let filtered = mockProperties;

    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(search) ||
          p.address.street.toLowerCase().includes(search) ||
          p.address.city.toLowerCase().includes(search) ||
          p.address.submarket.toLowerCase().includes(search)
      );
    }

    // Apply property class filter
    if (propertyClass !== 'all') {
      filtered = filtered.filter((p) => p.propertyDetails.propertyClass === propertyClass);
    }

    // Apply submarket filter
    if (submarket !== 'all') {
      filtered = filtered.filter((p) => p.address.submarket === submarket);
    }

    // Apply occupancy range filter
    if (occupancyRange !== 'all') {
      filtered = filtered.filter((p) => {
        const occ = p.operations.occupancy * 100;
        switch (occupancyRange) {
          case '95-100':
            return occ >= 95;
          case '90-95':
            return occ >= 90 && occ < 95;
          case '85-90':
            return occ >= 85 && occ < 90;
          case '0-85':
            return occ < 85;
          default:
            return true;
        }
      });
    }

    // Apply sorting
    const [sortField, sortDir] = sortBy.split('-');
    const sorted = [...filtered].sort((a, b) => {
      let aVal: number, bVal: number;

      switch (sortField) {
        case 'value':
          aVal = a.valuation.currentValue;
          bVal = b.valuation.currentValue;
          break;
        case 'noi':
          aVal = a.operations.noi;
          bVal = b.operations.noi;
          break;
        case 'irr':
          aVal = a.performance.irr;
          bVal = b.performance.irr;
          break;
        case 'units':
          aVal = a.propertyDetails.units;
          bVal = b.propertyDetails.units;
          break;
        default:
          return 0;
      }

      return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
    });

    return sorted;
  }, [searchTerm, propertyClass, submarket, occupancyRange, sortBy]);

  // Table-specific sorting
  const tableSortedProperties = useMemo(() => {
    if (viewMode !== 'table') return filteredAndSortedProperties;

    return [...filteredAndSortedProperties].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      switch (tableSortColumn) {
        case 'name':
          aVal = a.name;
          bVal = b.name;
          break;
        case 'submarket':
          aVal = a.address.submarket;
          bVal = b.address.submarket;
          break;
        case 'class':
          aVal = a.propertyDetails.propertyClass;
          bVal = b.propertyDetails.propertyClass;
          break;
        case 'units':
          aVal = a.propertyDetails.units;
          bVal = b.propertyDetails.units;
          break;
        case 'occupancy':
          aVal = a.operations.occupancy;
          bVal = b.operations.occupancy;
          break;
        case 'noi':
          aVal = a.operations.noi;
          bVal = b.operations.noi;
          break;
        case 'value':
          aVal = a.valuation.currentValue;
          bVal = b.valuation.currentValue;
          break;
        case 'irr':
          aVal = a.performance.irr;
          bVal = b.performance.irr;
          break;
        default:
          return 0;
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return tableSortDirection === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return tableSortDirection === 'asc' 
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [filteredAndSortedProperties, tableSortColumn, tableSortDirection, viewMode]);

  const handleTableSort = (column: string) => {
    if (tableSortColumn === column) {
      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setTableSortColumn(column as SortColumn);
      setTableSortDirection('desc');
    }
  };

  const handleViewDetails = (propertyId: string) => {
    navigate(`/properties/${propertyId}`);
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Investment Portfolio</h1>
            <p className="text-muted-foreground">
              Manage and monitor your real estate investments
            </p>
          </div>
        </div>

        {/* Summary Stats Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-muted animate-pulse rounded mb-2" />
                <div className="h-3 w-32 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters Card Skeleton */}
        <Card>
          <CardContent className="pt-6">
            <div className="h-10 w-full bg-muted animate-pulse rounded" />
          </CardContent>
        </Card>

        {/* Properties Grid Skeleton */}
        <PropertyCardSkeletonGrid count={6} />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Investment Portfolio</h1>
          <p className="text-muted-foreground">
            Manage and monitor your real estate investments
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summaryStats.totalProperties}</div>
            <p className="text-xs text-muted-foreground">
              Across 6 submarkets
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Units</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summaryStats.totalUnits.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Residential units
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(summaryStats.totalValue, true)}</div>
            <p className="text-xs text-muted-foreground">
              Current portfolio value
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Occupancy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPercent(summaryStats.avgOccupancy)}</div>
            <p className="text-xs text-muted-foreground">
              Portfolio average
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Toggle */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Properties</h2>
              <div className="flex gap-2">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3x3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'table' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('table')}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <PropertyFilters
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              propertyClass={propertyClass}
              onPropertyClassChange={setPropertyClass}
              submarket={submarket}
              onSubmarketChange={setSubmarket}
              occupancyRange={occupancyRange}
              onOccupancyRangeChange={setOccupancyRange}
              sortBy={sortBy}
              onSortByChange={setSortBy}
            />
          </div>
        </CardContent>
      </Card>

      {/* Properties Display */}
      <div>
        {filteredAndSortedProperties.length === 0 ? (
          <EmptyInvestments />
        ) : viewMode === 'grid' ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredAndSortedProperties.map((property) => (
              <PropertyCard
                key={property.id}
                property={property}
                onViewDetails={handleViewDetails}
              />
            ))}
          </div>
        ) : (
          <PropertyTable
            properties={tableSortedProperties}
            onSort={handleTableSort}
            sortColumn={tableSortColumn}
            sortDirection={tableSortDirection}
            onViewDetails={handleViewDetails}
          />
        )}
      </div>
    </div>
  );
}
