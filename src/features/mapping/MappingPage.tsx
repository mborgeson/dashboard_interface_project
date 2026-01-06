import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { MapPin, Maximize2, Layers } from 'lucide-react';
import type { Property } from '@/types';
import { mockProperties } from '@/data/mockProperties';
import { useMapFilters } from './hooks/useMapFilters';
import { MapFilterPanel } from './components/MapFilterPanel';
import { PropertyDetailPanel } from './components/PropertyDetailPanel';
import { MapLegend } from './components/MapLegend';
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

// Custom colored markers for different property classes
function createColoredIcon(propertyClass: 'A' | 'B' | 'C') {
  const colors = {
    A: '#2563eb', // blue-600
    B: '#16a34a', // green-600
    C: '#ea580c', // orange-600
  };

  const svgIcon = `
    <svg width="25" height="41" viewBox="0 0 25 41" xmlns="http://www.w3.org/2000/svg">
      <path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 8.4 12.5 28.5 12.5 28.5s12.5-20.1 12.5-28.5C25 5.6 19.4 0 12.5 0z" fill="${colors[propertyClass]}"/>
      <circle cx="12.5" cy="12.5" r="6" fill="white"/>
    </svg>
  `;

  return L.divIcon({
    html: svgIcon,
    className: 'custom-marker-icon',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  });
}

export function MappingPage() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [tileLayer, setTileLayer] = useState<'street' | 'satellite'>('street');

  const {
    filters,
    filteredProperties,
    clusteringEnabled,
    valueRange,
    togglePropertyClass,
    toggleSubmarket,
    setValueRange,
    setOccupancyRange,
    resetFilters,
    toggleClustering,
  } = useMapFilters(mockProperties);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) {
      return;
    }

    // Center on Phoenix, AZ area (defined inside effect as it's only used for initialization)
    const center: L.LatLngExpression = [33.4484, -112.074];
    const zoom = 10;

    // Create map instance
    const map = L.map(mapContainerRef.current, {
      center,
      zoom,
      scrollWheelZoom: true,
      zoomControl: false,
    });

    mapInstanceRef.current = map;

    // Add zoom control to top right
    L.control
      .zoom({
        position: 'topright',
      })
      .addTo(map);

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Cleanup on unmount
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        clusterGroupRef.current = null;
        markersLayerRef.current = null;
      }
    };
  }, []);

  // Update markers when filtered properties or clustering changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    const map = mapInstanceRef.current;

    // Remove existing layers
    if (clusterGroupRef.current) {
      map.removeLayer(clusterGroupRef.current);
      clusterGroupRef.current = null;
    }
    if (markersLayerRef.current) {
      map.removeLayer(markersLayerRef.current);
      markersLayerRef.current = null;
    }

    if (clusteringEnabled) {
      // Create marker cluster group
      const clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 15,
      });

      clusterGroupRef.current = clusterGroup;

      // Add markers to cluster group
      filteredProperties.forEach(property => {
        if (property.address.latitude && property.address.longitude) {
          const marker = L.marker(
            [property.address.latitude, property.address.longitude],
            {
              icon: createColoredIcon(property.propertyDetails.propertyClass),
            }
          );

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

          // Add click handler to show detail panel
          marker.on('click', () => {
            setSelectedProperty(property);
          });

          clusterGroup.addLayer(marker);
        }
      });

      // Add cluster group to map
      map.addLayer(clusterGroup);
    } else {
      // Create regular layer group (no clustering)
      const layerGroup = L.layerGroup();
      markersLayerRef.current = layerGroup;

      filteredProperties.forEach(property => {
        if (property.address.latitude && property.address.longitude) {
          const marker = L.marker(
            [property.address.latitude, property.address.longitude],
            {
              icon: createColoredIcon(property.propertyDetails.propertyClass),
            }
          );

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

          marker.on('click', () => {
            setSelectedProperty(property);
          });

          layerGroup.addLayer(marker);
        }
      });

      layerGroup.addTo(map);
    }
  }, [filteredProperties, clusteringEnabled]);

  // Zoom to fit all properties
  const handleZoomToFit = () => {
    if (!mapInstanceRef.current || filteredProperties.length === 0) return;

    const bounds = L.latLngBounds(
      filteredProperties
        .filter(p => p.address.latitude && p.address.longitude)
        .map(p => [p.address.latitude, p.address.longitude] as L.LatLngExpression)
    );

    mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] });
  };

  return (
    <div className="relative h-[calc(100vh-64px)]">
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Filter Panel */}
      <MapFilterPanel
        filters={filters}
        filteredCount={filteredProperties.length}
        totalCount={mockProperties.length}
        valueRange={valueRange}
        onTogglePropertyClass={togglePropertyClass}
        onToggleSubmarket={toggleSubmarket}
        onValueRangeChange={setValueRange}
        onOccupancyRangeChange={setOccupancyRange}
        onReset={resetFilters}
      />

      {/* Property Detail Panel */}
      {selectedProperty && (
        <PropertyDetailPanel
          property={selectedProperty}
          onClose={() => setSelectedProperty(null)}
        />
      )}

      {/* Map Legend */}
      <MapLegend />

      {/* Map Controls */}
      <div className="absolute bottom-4 left-4 z-[1000] space-y-2">
        {/* Zoom to Fit Button */}
        <button
          onClick={handleZoomToFit}
          className="bg-white rounded-lg shadow-md p-3 hover:bg-neutral-50 transition-colors flex items-center gap-2"
          title="Zoom to fit all properties"
        >
          <Maximize2 className="w-5 h-5 text-neutral-700" />
          <span className="text-sm font-medium text-neutral-700">Fit All</span>
        </button>

        {/* Toggle Clustering Button */}
        <button
          onClick={toggleClustering}
          className={`bg-white rounded-lg shadow-md p-3 hover:bg-neutral-50 transition-colors flex items-center gap-2 ${
            clusteringEnabled ? 'ring-2 ring-primary-500' : ''
          }`}
          title="Toggle marker clustering"
        >
          <MapPin className="w-5 h-5 text-neutral-700" />
          <span className="text-sm font-medium text-neutral-700">
            {clusteringEnabled ? 'Clustering On' : 'Clustering Off'}
          </span>
        </button>

        {/* Toggle Tile Layer Button */}
        <button
          onClick={() => setTileLayer(prev => (prev === 'street' ? 'satellite' : 'street'))}
          className="bg-white rounded-lg shadow-md p-3 hover:bg-neutral-50 transition-colors flex items-center gap-2"
          title="Toggle map view"
        >
          <Layers className="w-5 h-5 text-neutral-700" />
          <span className="text-sm font-medium text-neutral-700 capitalize">{tileLayer}</span>
        </button>
      </div>
    </div>
  );
}
