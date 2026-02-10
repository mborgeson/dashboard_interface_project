import { useEffect, useRef, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet.markercluster';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCurrency } from '@/lib/utils/formatters';
import type { SaleRecord, SalesFilters } from '../types';

// Fix for default marker icon issue in Vite
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

// ============================================================================
// Constants
// ============================================================================

const PHOENIX_CENTER: L.LatLngExpression = [33.45, -112.07];
const DEFAULT_ZOOM = 10;

// ============================================================================
// Helpers
// ============================================================================

/** Calculate months since a given date string */
function monthsSince(dateStr: string): number {
  const d = new Date(dateStr);
  const now = new Date();
  return (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
}

/** Get marker fill color based on sale recency */
function getMarkerColor(saleDate: string | null): string {
  if (!saleDate) return '#9ca3af'; // gray-400 for unknown
  const months = monthsSince(saleDate);
  if (months <= 12) return '#ef4444'; // red-500 — last 12 months
  if (months <= 36) return '#eab308'; // yellow-500 — 1-3 years
  if (months <= 60) return '#38bdf8'; // sky-400 — 3-5 years
  return '#9ca3af'; // gray-400 — 5+ years
}

/** Get marker radius based on sale price */
function getMarkerRadius(salePrice: number | null): number {
  if (salePrice == null) return 4;
  if (salePrice < 1_000_000) return 4;
  if (salePrice < 5_000_000) return 6;
  if (salePrice < 25_000_000) return 8;
  return 12;
}

/** Build popup HTML for a sale record */
function buildPopupContent(record: SaleRecord): string {
  const name = record.propertyName ?? 'Unknown Property';
  const date = record.saleDate
    ? new Date(record.saleDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'N/A';
  const price =
    record.salePrice != null ? formatCurrency(record.salePrice, true) : 'N/A';
  const units =
    record.numberOfUnits != null ? record.numberOfUnits.toLocaleString() : 'N/A';
  const ppu =
    record.pricePerUnit != null ? formatCurrency(record.pricePerUnit, true) : 'N/A';
  const buyer = record.buyerTrueCompany ?? 'N/A';

  return `
    <div class="p-2 min-w-[220px]">
      <div class="font-semibold text-neutral-900 mb-1">${name}</div>
      <div class="text-sm border-t border-neutral-200 pt-2 space-y-1">
        <div class="flex justify-between">
          <span class="text-neutral-600">Sale Date:</span>
          <span class="font-medium">${date}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Sale Price:</span>
          <span class="font-medium text-primary-600">${price}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Units:</span>
          <span class="font-medium">${units}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Price/Unit:</span>
          <span class="font-medium">${ppu}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Buyer:</span>
          <span class="font-medium max-w-[140px] truncate" title="${buyer}">${buyer}</span>
        </div>
      </div>
    </div>
  `;
}

/** Apply SalesFilters to a list of records (client-side) */
function applyFilters(
  data: SaleRecord[],
  filters?: SalesFilters
): SaleRecord[] {
  if (!filters) return data;
  return data.filter((r) => {
    if (filters.submarkets?.length && (!r.submarketCluster || !filters.submarkets.includes(r.submarketCluster)))
      return false;
    if (filters.minPrice != null && (r.salePrice == null || r.salePrice < filters.minPrice))
      return false;
    if (filters.maxPrice != null && (r.salePrice == null || r.salePrice > filters.maxPrice))
      return false;
    if (filters.dateFrom && (!r.saleDate || r.saleDate < filters.dateFrom))
      return false;
    if (filters.dateTo && (!r.saleDate || r.saleDate > filters.dateTo))
      return false;
    return true;
  });
}

// ============================================================================
// Component
// ============================================================================

interface SalesMapProps {
  data: SaleRecord[];
  isLoading: boolean;
  filters?: SalesFilters;
}

export function SalesMap({ data, isLoading, filters }: SalesMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  // Filter data and keep only records with valid coordinates
  const mappableRecords = useMemo(() => {
    const filtered = applyFilters(data, filters);
    return filtered.filter(
      (r): r is SaleRecord & { latitude: number; longitude: number } =>
        r.latitude != null && r.longitude != null
    );
  }, [data, filters]);

  // Initialize map (once)
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: PHOENIX_CENTER,
      zoom: DEFAULT_ZOOM,
      scrollWheelZoom: true,
    });

    mapInstanceRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        clusterGroupRef.current = null;
      }
    };
  }, []);

  // Update markers when data or filters change
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    const map = mapInstanceRef.current;

    // Remove previous cluster group
    if (clusterGroupRef.current) {
      map.removeLayer(clusterGroupRef.current);
      clusterGroupRef.current = null;
    }

    if (mappableRecords.length === 0) return;

    const clusterGroup = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 15,
    });

    clusterGroupRef.current = clusterGroup;

    mappableRecords.forEach((record) => {
      const marker = L.circleMarker([record.latitude, record.longitude], {
        radius: getMarkerRadius(record.salePrice),
        fillColor: getMarkerColor(record.saleDate),
        color: '#1f2937', // gray-800 border
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.7,
      });

      marker.bindPopup(buildPopupContent(record));
      clusterGroup.addLayer(marker);
    });

    map.addLayer(clusterGroup);
  }, [mappableRecords]);

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sales Map</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[600px] w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Sales Map</CardTitle>
        <span className="text-sm text-muted-foreground">
          {mappableRecords.length.toLocaleString()} mapped of{' '}
          {data.length.toLocaleString()} records
        </span>
      </CardHeader>
      <CardContent>
        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 mb-3 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Recency:</span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-red-500" />
            &lt;1 yr
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-yellow-500" />
            1-3 yr
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-sky-400" />
            3-5 yr
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full bg-gray-400" />
            5+ yr
          </span>
          <span className="ml-4 font-medium text-foreground">Size = price</span>
        </div>

        {/* Map container */}
        <div
          ref={mapContainerRef}
          className="h-[600px] w-full rounded-lg overflow-hidden border border-neutral-200"
        />
      </CardContent>
    </Card>
  );
}
