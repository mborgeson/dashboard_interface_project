import { useState, memo, useCallback } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';
import type { Property } from '@/types';

interface PropertyTableProps {
  properties: Property[];
  onSort: (column: string) => void;
  sortColumn: string;
  sortDirection: 'asc' | 'desc';
  onViewDetails?: (propertyId: string) => void;
}

// Memoized SortIcon to avoid re-renders
const SortIcon = memo(function SortIcon({ column, sortColumn, sortDirection }: { column: string; sortColumn: string; sortDirection: 'asc' | 'desc' }) {
  if (sortColumn !== column) return null;
  return sortDirection === 'asc' ? (
    <ChevronUp className="ml-1 inline h-4 w-4" />
  ) : (
    <ChevronDown className="ml-1 inline h-4 w-4" />
  );
});

// Memoized table row component for better list performance
interface PropertyRowProps {
  property: Property;
  index: number;
  isExpanded: boolean;
  onToggle: (id: string) => void;
  onViewDetails?: (propertyId: string) => void;
}

const PropertyRow = memo(function PropertyRow({
  property,
  index,
  isExpanded,
  onToggle,
  onViewDetails
}: PropertyRowProps) {
  const handleClick = useCallback(() => {
    onToggle(property.id);
  }, [onToggle, property.id]);

  const handleViewDetails = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onViewDetails?.(property.id);
  }, [onViewDetails, property.id]);

  return (
    <>
      <TableRow
        className={`cursor-pointer ${index % 2 === 0 ? 'bg-muted/30' : ''}`}
        onClick={handleClick}
      >
        <TableCell className="font-medium">
          <div>
            <div>{property.name}</div>
            <div className="text-xs text-muted-foreground">
              {property.address.city}, {property.address.state}
            </div>
          </div>
        </TableCell>
        <TableCell>{property.address.submarket}</TableCell>
        <TableCell>
          <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold">
            Class {property.propertyDetails.propertyClass}
          </span>
        </TableCell>
        <TableCell className="text-right">{property.propertyDetails.units}</TableCell>
        <TableCell className="text-right">
          {formatPercent(property.operations.occupancy)}
        </TableCell>
        <TableCell className="text-right">
          {formatCurrency(property.operations.noi, true)}
        </TableCell>
        <TableCell className="text-right">
          {formatCurrency(property.valuation.currentValue, true)}
        </TableCell>
        <TableCell className="text-right">
          <span className="font-semibold text-green-600">
            {formatPercent(property.performance.irr)}
          </span>
        </TableCell>
      </TableRow>
      {isExpanded && (
        <TableRow>
          <TableCell colSpan={8} className="bg-muted/20">
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Address</p>
                  <p className="mt-1 text-sm">
                    {property.address.street}
                    <br />
                    {property.address.city}, {property.address.state} {property.address.zip}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Property Details</p>
                  <p className="mt-1 text-sm">
                    {property.propertyDetails.squareFeet.toLocaleString()} sq ft
                    <br />
                    Built: {property.propertyDetails.yearBuilt}
                    <br />
                    Type: {property.propertyDetails.assetType}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Financial Metrics</p>
                  <p className="mt-1 text-sm">
                    Cap Rate: {formatPercent(property.valuation.capRate)}
                    <br />
                    CoC Return: {formatPercent(property.performance.cashOnCashReturn)}
                    <br />
                    Equity Multiple: {property.performance.equityMultiple.toFixed(2)}x
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Operations</p>
                  <p className="mt-1 text-sm">
                    Avg Rent: {formatCurrency(property.operations.averageRent)}
                    <br />
                    Monthly Revenue: {formatCurrency(property.operations.monthlyRevenue, true)}
                    <br />
                    OpEx Ratio: {formatPercent(property.operations.operatingExpenseRatio)}
                  </p>
                </div>
              </div>
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleViewDetails}
                >
                  View Full Details
                </Button>
              </div>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
});

export function PropertyTable({ properties, onSort, sortColumn, sortDirection, onViewDetails }: PropertyTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // Memoized toggle handler to maintain stable reference
  const toggleRow = useCallback((propertyId: string) => {
    setExpandedRow(prev => prev === propertyId ? null : propertyId);
  }, []);

  // Memoized sort handlers for stable references
  const handleSortName = useCallback(() => onSort('name'), [onSort]);
  const handleSortSubmarket = useCallback(() => onSort('submarket'), [onSort]);
  const handleSortClass = useCallback(() => onSort('class'), [onSort]);
  const handleSortUnits = useCallback(() => onSort('units'), [onSort]);
  const handleSortOccupancy = useCallback(() => onSort('occupancy'), [onSort]);
  const handleSortNoi = useCallback(() => onSort('noi'), [onSort]);
  const handleSortValue = useCallback(() => onSort('value'), [onSort]);
  const handleSortIrr = useCallback(() => onSort('irr'), [onSort]);

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead
              className="cursor-pointer hover:bg-muted/50"
              onClick={handleSortName}
            >
              Property Name
              <SortIcon column="name" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer hover:bg-muted/50"
              onClick={handleSortSubmarket}
            >
              Submarket
              <SortIcon column="submarket" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer hover:bg-muted/50"
              onClick={handleSortClass}
            >
              Class
              <SortIcon column="class" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={handleSortUnits}
            >
              Units
              <SortIcon column="units" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={handleSortOccupancy}
            >
              Occupancy
              <SortIcon column="occupancy" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={handleSortNoi}
            >
              NOI
              <SortIcon column="noi" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={handleSortValue}
            >
              Value
              <SortIcon column="value" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={handleSortIrr}
            >
              IRR
              <SortIcon column="irr" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {properties.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} className="h-24 text-center">
                No properties found.
              </TableCell>
            </TableRow>
          ) : (
            properties.map((property, index) => (
              <PropertyRow
                key={property.id}
                property={property}
                index={index}
                isExpanded={expandedRow === property.id}
                onToggle={toggleRow}
                onViewDetails={onViewDetails}
              />
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
