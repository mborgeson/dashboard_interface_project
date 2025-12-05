import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface PropertyFiltersProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  propertyClass: string;
  onPropertyClassChange: (value: string) => void;
  submarket: string;
  onSubmarketChange: (value: string) => void;
  occupancyRange: string;
  onOccupancyRangeChange: (value: string) => void;
  sortBy: string;
  onSortByChange: (value: string) => void;
}

export function PropertyFilters({
  searchTerm,
  onSearchChange,
  propertyClass,
  onPropertyClassChange,
  submarket,
  onSubmarketChange,
  occupancyRange,
  onOccupancyRangeChange,
  sortBy,
  onSortByChange,
}: PropertyFiltersProps) {
  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search properties..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Filters Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        {/* Property Class Filter */}
        <Select value={propertyClass} onValueChange={onPropertyClassChange}>
          <SelectTrigger>
            <SelectValue placeholder="Property Class" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Classes</SelectItem>
            <SelectItem value="A">Class A</SelectItem>
            <SelectItem value="B">Class B</SelectItem>
            <SelectItem value="C">Class C</SelectItem>
          </SelectContent>
        </Select>

        {/* Submarket Filter */}
        <Select value={submarket} onValueChange={onSubmarketChange}>
          <SelectTrigger>
            <SelectValue placeholder="Submarket" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Submarkets</SelectItem>
            <SelectItem value="Scottsdale">Scottsdale</SelectItem>
            <SelectItem value="Tempe">Tempe</SelectItem>
            <SelectItem value="Mesa">Mesa</SelectItem>
            <SelectItem value="Gilbert">Gilbert</SelectItem>
            <SelectItem value="Chandler">Chandler</SelectItem>
            <SelectItem value="Phoenix Central">Phoenix Central</SelectItem>
          </SelectContent>
        </Select>

        {/* Occupancy Range Filter */}
        <Select value={occupancyRange} onValueChange={onOccupancyRangeChange}>
          <SelectTrigger>
            <SelectValue placeholder="Occupancy" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Occupancy</SelectItem>
            <SelectItem value="95-100">95-100%</SelectItem>
            <SelectItem value="90-95">90-95%</SelectItem>
            <SelectItem value="85-90">85-90%</SelectItem>
            <SelectItem value="0-85">Below 85%</SelectItem>
          </SelectContent>
        </Select>

        {/* Sort By */}
        <Select value={sortBy} onValueChange={onSortByChange}>
          <SelectTrigger>
            <SelectValue placeholder="Sort By" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="value-desc">Value (High to Low)</SelectItem>
            <SelectItem value="value-asc">Value (Low to High)</SelectItem>
            <SelectItem value="noi-desc">NOI (High to Low)</SelectItem>
            <SelectItem value="noi-asc">NOI (Low to High)</SelectItem>
            <SelectItem value="irr-desc">IRR (High to Low)</SelectItem>
            <SelectItem value="irr-asc">IRR (Low to High)</SelectItem>
            <SelectItem value="units-desc">Units (High to Low)</SelectItem>
            <SelectItem value="units-asc">Units (Low to High)</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
