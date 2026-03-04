import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { MapPin } from 'lucide-react';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [20, 33],
  iconAnchor: [10, 33],
  popupAnchor: [0, -33],
  shadowSize: [33, 33],
});

interface DealAerialMapProps {
  latitude?: number;
  longitude?: number;
}

export function DealAerialMap({ latitude, longitude }: DealAerialMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || latitude == null || longitude == null) return;
    if (mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [latitude, longitude],
      zoom: 15,
      zoomControl: false,
      attributionControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      touchZoom: false,
    });

    mapRef.current = map;

    // Esri World Imagery satellite tile layer (free, no API key)
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 19 },
    ).addTo(map);

    L.marker([latitude, longitude], { icon: DefaultIcon }).addTo(map);

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [latitude, longitude]);

  if (latitude == null || longitude == null) {
    return (
      <div className="h-[100px] w-full rounded bg-neutral-50 flex items-center justify-center text-xs text-neutral-400 gap-1">
        <MapPin className="w-3 h-3" />
        No location data
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[100px] w-full rounded overflow-hidden border border-neutral-200"
    />
  );
}
