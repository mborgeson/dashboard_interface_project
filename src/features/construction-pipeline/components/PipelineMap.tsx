import { useEffect, useRef, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet.markercluster';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { ProjectRecord } from '../types';

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

const STATUS_COLORS: Record<string, string> = {
  proposed: '#9ca3af',
  final_planning: '#eab308',
  permitted: '#f97316',
  under_construction: '#ef4444',
  delivered: '#22c55e',
};

const STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  final_planning: 'Final Planning',
  permitted: 'Permitted',
  under_construction: 'Under Construction',
  delivered: 'Delivered',
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  CONV_MR: 'Conventional/Market-Rate',
  CONV_CONDO: 'Conventional/Condo',
  BTR: 'Build-to-Rent',
  LIHTC: 'LIHTC (Affordable)',
  AGE_55: 'Age-Restricted (55+)',
  WORKFORCE: 'Workforce Housing',
  MIXED_USE: 'Mixed-Use',
  CONVERSION: 'Conversion',
};

// ============================================================================
// Helpers
// ============================================================================

function getMarkerColor(status: string | null): string {
  if (!status) return '#9ca3af';
  return STATUS_COLORS[status] ?? '#9ca3af';
}

function getMarkerRadius(units: number | null): number {
  if (units == null) return 4;
  if (units < 100) return 4;
  if (units < 200) return 6;
  if (units < 400) return 8;
  return 12;
}

const numFmt = new Intl.NumberFormat('en-US');

function buildPopupContent(record: ProjectRecord): string {
  const name = record.projectName ?? 'Unknown Project';
  const status = record.pipelineStatus
    ? STATUS_LABELS[record.pipelineStatus] ?? record.pipelineStatus
    : 'N/A';
  const classification = record.primaryClassification
    ? CLASSIFICATION_LABELS[record.primaryClassification] ?? record.primaryClassification
    : 'N/A';
  const developer = record.developerName ?? 'N/A';
  const units =
    record.numberOfUnits != null ? numFmt.format(record.numberOfUnits) : 'N/A';
  const delivery = record.estimatedDeliveryDate
    ? new Date(record.estimatedDeliveryDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
      })
    : 'N/A';

  return `
    <div class="p-2 min-w-[220px]">
      <div class="font-semibold text-neutral-900 mb-1">${name}</div>
      <div class="text-sm border-t border-neutral-200 pt-2 space-y-1">
        <div class="flex justify-between">
          <span class="text-neutral-600">Status:</span>
          <span class="font-medium">${status}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Type:</span>
          <span class="font-medium">${classification}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Units:</span>
          <span class="font-medium">${units}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Developer:</span>
          <span class="font-medium max-w-[140px] truncate" title="${developer}">${developer}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-neutral-600">Delivery:</span>
          <span class="font-medium">${delivery}</span>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// Component
// ============================================================================

interface PipelineMapProps {
  data: ProjectRecord[];
  isLoading: boolean;
}

export function PipelineMap({ data, isLoading }: PipelineMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  // Filter to records with valid coordinates
  const mappableRecords = useMemo(() => {
    return data.filter(
      (r): r is ProjectRecord & { latitude: number; longitude: number } =>
        r.latitude != null && r.longitude != null,
    );
  }, [data]);

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

  // Update markers when data changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    const map = mapInstanceRef.current;

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
        radius: getMarkerRadius(record.numberOfUnits),
        fillColor: getMarkerColor(record.pipelineStatus),
        color: '#1f2937',
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.7,
      });

      marker.bindPopup(buildPopupContent(record));
      clusterGroup.addLayer(marker);
    });

    map.addLayer(clusterGroup);
  }, [mappableRecords]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Map</CardTitle>
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
        <CardTitle>Pipeline Map</CardTitle>
        <span className="text-sm text-muted-foreground">
          {mappableRecords.length.toLocaleString()} mapped of{' '}
          {data.length.toLocaleString()} projects
        </span>
      </CardHeader>
      <CardContent>
        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 mb-3 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Status:</span>
          {Object.entries(STATUS_LABELS).map(([key, label]) => (
            <span key={key} className="flex items-center gap-1">
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ backgroundColor: STATUS_COLORS[key] }}
              />
              {label}
            </span>
          ))}
          <span className="ml-4 font-medium text-foreground">Size = units</span>
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
