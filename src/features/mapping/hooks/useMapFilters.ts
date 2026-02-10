import { useState, useMemo } from 'react';
import type { Property } from '@/types';

// Phoenix city center fallback coordinates used by the backend for missing lat/lng
const FALLBACK_LAT = 33.45;
const FALLBACK_LNG = -112.07;

function hasValidCoordinates(property: Property): boolean {
  const { latitude, longitude } = property.address;
  if (!latitude || !longitude) return false;
  return !(latitude === FALLBACK_LAT && longitude === FALLBACK_LNG);
}

export interface MapFilters {
  propertyClasses: Set<'A' | 'B' | 'C'>;
  submarkets: Set<string>;
  valueRange: [number, number];
  occupancyRange: [number, number];
}

const DEFAULT_FILTERS: MapFilters = {
  propertyClasses: new Set(['A', 'B', 'C']),
  submarkets: new Set<string>([
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
  ]),
  valueRange: [0, 100000000],
  occupancyRange: [0, 100],
};

export function useMapFilters(properties: Property[]) {
  const [filters, setFilters] = useState<MapFilters>(DEFAULT_FILTERS);
  const [clusteringEnabled, setClusteringEnabled] = useState(true);

  // Calculate value range from properties
  const valueRange = useMemo((): [number, number] => {
    if (properties.length === 0) return [0, 100000000];
    const values = properties.map(p => p.valuation.currentValue);
    return [Math.min(...values), Math.max(...values)];
  }, [properties]);

  // Filter properties based on current filters
  const filteredProperties = useMemo(() => {
    return properties.filter(property => {
      // Property class filter
      if (!filters.propertyClasses.has(property.propertyDetails.propertyClass)) {
        return false;
      }

      // Submarket filter
      if (!filters.submarkets.has(property.address.submarket)) {
        return false;
      }

      // Value range filter
      if (
        property.valuation.currentValue < filters.valueRange[0] ||
        property.valuation.currentValue > filters.valueRange[1]
      ) {
        return false;
      }

      // Occupancy range filter (convert to percentage)
      const occupancyPercent = property.operations.occupancy * 100;
      if (
        occupancyPercent < filters.occupancyRange[0] ||
        occupancyPercent > filters.occupancyRange[1]
      ) {
        return false;
      }

      return true;
    });
  }, [properties, filters]);

  // Separate filtered properties into mappable (valid coords) and excluded (fallback/missing coords)
  const { mappableProperties, excludedCoordinateCount } = useMemo(() => {
    const mappable: Property[] = [];
    let excluded = 0;
    for (const property of filteredProperties) {
      if (hasValidCoordinates(property)) {
        mappable.push(property);
      } else {
        excluded++;
      }
    }
    return { mappableProperties: mappable, excludedCoordinateCount: excluded };
  }, [filteredProperties]);

  const togglePropertyClass = (propertyClass: 'A' | 'B' | 'C') => {
    setFilters(prev => {
      const newClasses = new Set(prev.propertyClasses);
      if (newClasses.has(propertyClass)) {
        newClasses.delete(propertyClass);
      } else {
        newClasses.add(propertyClass);
      }
      return { ...prev, propertyClasses: newClasses };
    });
  };

  const toggleSubmarket = (submarket: string) => {
    setFilters(prev => {
      const newSubmarkets = new Set(prev.submarkets);
      if (newSubmarkets.has(submarket)) {
        newSubmarkets.delete(submarket);
      } else {
        newSubmarkets.add(submarket);
      }
      return { ...prev, submarkets: newSubmarkets };
    });
  };

  const setValueRange = (range: [number, number]) => {
    setFilters(prev => ({ ...prev, valueRange: range }));
  };

  const setOccupancyRange = (range: [number, number]) => {
    setFilters(prev => ({ ...prev, occupancyRange: range }));
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const toggleClustering = () => {
    setClusteringEnabled(prev => !prev);
  };

  return {
    filters,
    filteredProperties,
    mappableProperties,
    excludedCoordinateCount,
    clusteringEnabled,
    valueRange,
    togglePropertyClass,
    toggleSubmarket,
    setValueRange,
    setOccupancyRange,
    resetFilters,
    toggleClustering,
  };
}
