import { useState } from 'react';
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

// Move SortIcon outside to avoid creating during render
function SortIcon({ column, sortColumn, sortDirection }: { column: string; sortColumn: string; sortDirection: 'asc' | 'desc' }) {
  if (sortColumn !== column) return null;
  return sortDirection === 'asc' ? (
    <ChevronUp className="ml-1 inline h-4 w-4" />
  ) : (
    <ChevronDown className="ml-1 inline h-4 w-4" />
  );
}

export function PropertyTable({ properties, onSort, sortColumn, sortDirection, onViewDetails }: PropertyTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const toggleRow = (propertyId: string) => {
    setExpandedRow(expandedRow === propertyId ? null : propertyId);
  };

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead 
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onSort('name')}
            >
              Property Name
              <SortIcon column="name" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onSort('submarket')}
            >
              Submarket
              <SortIcon column="submarket" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onSort('class')}
            >
              Class
              <SortIcon column="class" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={() => onSort('units')}
            >
              Units
              <SortIcon column="units" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={() => onSort('occupancy')}
            >
              Occupancy
              <SortIcon column="occupancy" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={() => onSort('noi')}
            >
              NOI
              <SortIcon column="noi" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={() => onSort('value')}
            >
              Value
              <SortIcon column="value" sortColumn={sortColumn} sortDirection={sortDirection} />
            </TableHead>
            <TableHead 
              className="cursor-pointer text-right hover:bg-muted/50"
              onClick={() => onSort('irr')}
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
              <>
                <TableRow
                  key={property.id}
                  className={`cursor-pointer ${index % 2 === 0 ? 'bg-muted/30' : ''}`}
                  onClick={() => toggleRow(property.id)}
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
                {expandedRow === property.id && (
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
                            onClick={(e) => {
                              e.stopPropagation();
                              onViewDetails?.(property.id);
                            }}
                          >
                            View Full Details
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
