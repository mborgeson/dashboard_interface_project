import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import type { Property } from '@/types';
import { formatCurrency } from '@/lib/utils/formatters';

// Fix for default marker icon issue
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

interface PropertyMapProps {
  properties: Property[];
}

export function PropertyMap({ properties }: PropertyMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  // Center on Phoenix, AZ area
  const center: L.LatLngExpression = [33.4484, -112.074];
  const zoom = 10;

  useEffect(() => {
    // Only initialize if container exists and map doesn't
    if (!mapContainerRef.current || mapInstanceRef.current) {
      return;
    }

    // Create map instance
    const map = L.map(mapContainerRef.current, {
      center,
      zoom,
      scrollWheelZoom: true,
    });

    mapInstanceRef.current = map;

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Create marker cluster group
    const clusterGroup = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 15,
    });

    clusterGroupRef.current = clusterGroup;

    // Add markers to cluster group
    properties.forEach((property) => {
      if (property.address.latitude && property.address.longitude) {
        const marker = L.marker([property.address.latitude, property.address.longitude]);

        const popupContent = `
          <div class="p-2 min-w-[200px]">
            <div class="font-semibold text-neutral-900 mb-1">${property.name}</div>
            <div class="text-sm text-neutral-600 mb-2">
              ${property.address.street}<br/>
              ${property.address.city}, ${property.address.state} ${property.address.zip}
            </div>
            <div class="text-sm border-t border-neutral-200 pt-2 space-y-1">
              <div class="flex justify-between">
                <span class="text-neutral-600">Units:</span>
                <span class="font-medium">${property.propertyDetails.units}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-neutral-600">Class:</span>
                <span class="font-medium">${property.propertyDetails.propertyClass}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-neutral-600">Value:</span>
                <span class="font-medium text-primary-600">${formatCurrency(property.valuation.currentValue, true)}</span>
              </div>
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        clusterGroup.addLayer(marker);
      }
    });

    // Add cluster group to map
    map.addLayer(clusterGroup);

    // Cleanup on unmount
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        clusterGroupRef.current = null;
      }
    };
  }, [properties]);

  return (
    <div
      ref={mapContainerRef}
      className="h-[400px] rounded-lg overflow-hidden border border-neutral-200 shadow-sm"
    />
  );
}
