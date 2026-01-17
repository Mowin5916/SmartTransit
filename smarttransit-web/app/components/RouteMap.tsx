'use client';

import React, { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { GoogleMap, useLoadScript, Polyline, Marker } from '@react-google-maps/api';

type Props = {
  origin?: { lat: number; lng: number } | null;
  destination?: { lat: number; lng: number } | null;
  waypoints?: { name: string; lat: number; lng: number }[];
  startAnimate?: boolean;
  busCount?: number;
  busSpeed?: number;
  mapHeight?: string;
};

// 'geometry' is required for calculating heading (bus rotation)
const GOOGLE_LIBS: ("places" | "geometry")[] = ['places', 'geometry'];
const DEFAULT_CENTER = { lat: 12.9716, lng: 77.5946 };

// High-Fidelity Bus Icon
const REALISTIC_BUS_ICON = {
  path: "M4 10c0-1.1.9-2 2-2h12c1.1 0 2 .9 2 2v3h1.5a.5.5 0 0 1 0 1H20v3a1 1 0 0 1-1 1h-1v1a1 1 0 0 1-2 0v-1H8v1a1 1 0 0 1-2 0v-1H5a1 1 0 0 1-1-1v-3H2.5a.5.5 0 0 1 0-1H4v-3zm2 0v3h12v-3H6zm-2 5h16v1.5H4V15z M6 11h2v1H6v-1zm10 0h2v1h-2v-1z",
  fillColor: "#F59E0B", // Amber
  fillOpacity: 1,
  strokeWeight: 1,
  strokeColor: "#000",
  scale: 1.5,
  anchor: { x: 10, y: 10 }
};

// Simple Circle for Stops
const CIRCLE_PATH = "M 0, 0 m -2, 0 a 2, 2 0 1, 0 4, 0 a 2, 2 0 1, 0 -4, 0";

export default function RouteMap({
  origin, destination, waypoints = [], startAnimate = false, busCount = 1, busSpeed = 2, mapHeight = '520px'
}: Props) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
  const { isLoaded } = useLoadScript({ googleMapsApiKey: apiKey, libraries: GOOGLE_LIBS });

  const mapRef = useRef<google.maps.Map | null>(null);
  const directionsServiceRef = useRef<google.maps.DirectionsService | null>(null);
  const [routePath, setRoutePath] = useState<google.maps.LatLng[]>([]);
  
  const markersRef = useRef<google.maps.Marker[]>([]);
  const indicesRef = useRef<number[]>([]);
  const animRef = useRef<number | null>(null);

  const stopIcon = useMemo(() => ({
    path: CIRCLE_PATH,
    fillColor: "#3B82F6",
    fillOpacity: 1,
    strokeWeight: 2,
    strokeColor: "#fff",
    scale: 4 
  }), []);

  const onMapLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
    directionsServiceRef.current = new google.maps.DirectionsService();
  }, []);

  // --- CALCULATE ROUTE ---
  useEffect(() => {
    if (!isLoaded || !origin || !destination) return;
    if (!directionsServiceRef.current) return;

    // Convert props to Google Maps Waypoints
    const waypts = waypoints.map(pt => ({ 
      location: { lat: pt.lat, lng: pt.lng }, 
      stopover: true 
    }));

    directionsServiceRef.current.route(
      {
        origin: origin,
        destination: destination,
        waypoints: waypts,
        travelMode: google.maps.TravelMode.DRIVING,
        // THIS IS THE KEY SETTING FOR SHORTEST PATH (TSP)
        optimizeWaypoints: true, 
      },
      (result, status) => {
        if (status === google.maps.DirectionsStatus.OK && result && result.routes[0]) {
          const detailedPath = result.routes[0].overview_path;
          setRoutePath(detailedPath);
          
          // Fit map to show full route
          const bounds = new google.maps.LatLngBounds();
          detailedPath.forEach(p => bounds.extend(p));
          mapRef.current?.fitBounds(bounds);
        } else {
          console.error("Directions request failed due to " + status);
          // Fallback: Draw straight lines if API fails
          const fallback = [
             new google.maps.LatLng(origin.lat, origin.lng),
             ...waypoints.map(w => new google.maps.LatLng(w.lat, w.lng)),
             new google.maps.LatLng(destination.lat, destination.lng)
          ];
          setRoutePath(fallback);
        }
      }
    );
  }, [isLoaded, origin, destination, waypoints]);

  // --- CREATE BUS MARKERS ---
  useEffect(() => {
    // Clear existing markers
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];
    indicesRef.current = [];

    if (!mapRef.current || routePath.length === 0) return;

    const safeBusCount = Math.max(1, busCount || 1);
    const totalPoints = routePath.length;
    const spacing = Math.floor(totalPoints / safeBusCount);

    for (let i = 0; i < safeBusCount; i++) {
      const startIndex = (i * spacing) % totalPoints;
      indicesRef.current.push(startIndex);
      const marker = new google.maps.Marker({
        position: routePath[startIndex],
        map: mapRef.current,
        icon: { ...REALISTIC_BUS_ICON, rotation: 0 } as any,
        title: `Bus ${i+1}`,
        zIndex: 100 // Keep bus on top of route line
      });
      markersRef.current.push(marker);
    }
  }, [routePath, busCount]);

  // --- ANIMATION LOOP ---
  useEffect(() => {
    if (!startAnimate || routePath.length === 0) {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      return;
    }

    const animate = () => {
      markersRef.current.forEach((marker, i) => {
        let idx = indicesRef.current[i];
        const currentPos = routePath[Math.floor(idx)];
        
        // Look ahead for smooth rotation
        const lookAheadIdx = (Math.floor(idx) + 4) % routePath.length;
        const nextPos = routePath[lookAheadIdx];
        
        // Update index based on speed
        idx = (idx + (busSpeed * 0.5)) % routePath.length; 
        indicesRef.current[i] = idx;
        
        const floorIdx = Math.floor(idx);
        if (routePath[floorIdx]) {
            marker.setPosition(routePath[floorIdx]);
        }

        // Calculate Rotation using Geometry library
        if (window.google && window.google.maps && window.google.maps.geometry && currentPos && nextPos) {
             const heading = google.maps.geometry.spherical.computeHeading(currentPos, nextPos);
             const icon = marker.getIcon() as any;
             icon.rotation = heading;
             marker.setIcon(icon);
        }
      });
      animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [startAnimate, routePath, busSpeed]);

  if (!isLoaded) return <div className="text-zinc-500 p-4 animate-pulse">Loading Satellite Data...</div>;

  return (
    <div style={{ width: '100%', height: mapHeight, borderRadius: '0.75rem', overflow: 'hidden' }}>
      <GoogleMap
        mapContainerStyle={{ width: '100%', height: '100%' }}
        center={DEFAULT_CENTER}
        zoom={12}
        onLoad={onMapLoad}
        options={{
          streetViewControl: false, mapTypeControl: false, fullscreenControl: false,
          styles: [
            { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
            { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
            { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] }
          ]
        }}
      >
        {routePath.length > 0 && <Polyline path={routePath} options={{ strokeColor: "#8b5cf6", strokeOpacity: 0.8, strokeWeight: 5 }} />}
        
        {/* Render Stop Markers */}
        {waypoints.map((wp, idx) => (
            <Marker key={idx} position={{ lat: wp.lat, lng: wp.lng }} icon={stopIcon as any} title={wp.name} />
        ))}
        {/* Origin/Dest Markers */}
        {origin && <Marker position={origin} title="Start" />}
        {destination && <Marker position={destination} title="End" />}
      </GoogleMap>
    </div>
  );
}