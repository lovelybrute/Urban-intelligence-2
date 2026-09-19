import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Bus, Route, UrbanEvent } from "../types";
import { Layers } from "lucide-react";

interface GisMapProps {
  buses: Bus[];
  routes: Route[];
  events: UrbanEvent[];
  onSelectEvent: (event: UrbanEvent) => void;
  selectedEventId?: number;
  height?: string;
}

export const GisMap: React.FC<GisMapProps> = ({
  buses,
  routes,
  events,
  onSelectEvent,
  selectedEventId,
  height = "calc(100vh - 140px)",
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const routesLayerRef = useRef<L.LayerGroup | null>(null);

  const [layersOpen, setLayersOpen] = useState(false);

  // Layer filter toggles
  const [showBuses, setShowBuses] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const [showDefects, setShowDefects] = useState(true);
  const [showCongestion, setShowCongestion] = useState(true);
  const [showSafety, setShowSafety] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Hyderabad City Center: 17.4100, 78.4700
    const map = L.map(mapContainerRef.current, {
      center: [17.41, 78.47],
      zoom: 12,
      zoomControl: false,
    });

    // Custom dark sleek map tiles (CartoDB Dark Matter)
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://carto.com/">CartoDB</a> &copy; OpenStreetMap contributors',
        maxZoom: 19,
        subdomains: "abcd",
      },
    ).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    routesLayerRef.current = L.layerGroup().addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    const resize = new ResizeObserver(() => map.invalidateSize());
    resize.observe(mapContainerRef.current);
    return () => {
      resize.disconnect();
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Route Polylines
  useEffect(() => {
    if (!mapInstanceRef.current || !routesLayerRef.current) return;
    routesLayerRef.current.clearLayers();

    if (showRoutes) {
      routes.forEach((rt, idx) => {
        const colors = ["#2563eb", "#38bdf8", "#8b5cf6", "#3b82f6", "#10b981"];
        const color = colors[idx % colors.length];

        const polyline = L.polyline(rt.waypoints, {
          color: color,
          weight: 3.5,
          opacity: 0.65,
          dashArray: "6, 8",
        });

        polyline.bindTooltip(`<b>${rt.route_number}:</b> ${rt.name}`, {
          sticky: true,
          className: "panel",
        });

        polyline.addTo(routesLayerRef.current!);
      });
    }
  }, [routes, showRoutes]);

  // Update Markers (Buses, Defects, Congestion, Safety, Incidents)
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    // 1. Bus Markers
    if (showBuses) {
      buses.forEach((bus) => {
        const busIcon = L.divIcon({
          className: "custom-bus-marker",
          html: `
            <div style="
              width: 30px;
              height: 30px;
              border-radius: 50%;
              background: #2563eb;
              border: 2px solid #ffffff;
              box-shadow: 0 2px 8px rgba(0,0,0,0.5);
              display: flex;
              align-items: center;
              justify-content: center;
              color: #ffffff;
              font-weight: 700;
              font-size: 11px;
              transform: rotate(${bus.heading || 0}deg);
            ">
              🚌
            </div>
            <div style="
              position: absolute;
              bottom: -18px;
              left: 50%;
              transform: translateX(-50%);
              background: #18181b;
              color: #fafafa;
              font-size: 9px;
              font-weight: 600;
              padding: 1px 5px;
              border-radius: 4px;
              white-space: nowrap;
              border: 1px solid rgba(255,255,255,0.1);
              box-shadow: 0 2px 6px rgba(0,0,0,0.4);
            ">
              ${bus.bus_number}
            </div>
          `,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        });

        const marker = L.marker([bus.current_latitude, bus.current_longitude], {
          icon: busIcon,
        });
        marker.bindPopup(`
          <div style="padding: 6px; font-family: Inter, system-ui, sans-serif;">
            <div style="font-weight: 700; color: #2563eb; font-size: 13px;">${bus.bus_number}</div>
            <div style="font-size: 11px; color: #a1a1aa; margin-bottom: 6px;">${bus.route_name || "Active Corridor"}</div>
            <div style="font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
              <div>Speed: <b>${bus.speed} km/h</b></div>
              <div>Edge FPS: <b style="color:#22c55e;">${bus.edge_fps ?? "Unavailable"}</b></div>
              <div>Cams: <b>${bus.active_cameras ?? "Unavailable"} HD</b></div>
              <div>Load: <b>${bus.passenger_load_pct || 60}%</b></div>
            </div>
          </div>
        `);
        marker.addTo(markersLayerRef.current!);
      });
    }

    // 2. Urban Events Markers
    events.forEach((evt) => {
      let isVisible = false;
      let markerColor = "#d97706";
      let iconSymbol = "⚠️";

      if (
        [
          "pothole",
          "crack",
          "damaged_road",
          "damaged_divider",
          "missing_sign",
        ].includes(evt.event_type)
      ) {
        isVisible = showDefects;
        markerColor =
          evt.severity === "critical"
            ? "#dc2626"
            : evt.severity === "high"
              ? "#ea580c"
              : "#d97706";
        iconSymbol = evt.event_type === "pothole" ? "🕳️" : "⚠️";
      } else if (evt.event_type === "waterlogging") {
        isVisible = showDefects;
        markerColor = "#0284c7";
        iconSymbol = "🌊";
      } else if (evt.event_type === "congestion") {
        isVisible = showCongestion;
        markerColor = "#db2777";
        iconSymbol = "🚗";
      } else if (evt.event_type === "pedestrian_risk") {
        isVisible = showSafety;
        markerColor = "#eab308";
        iconSymbol = "🚶";
      } else if (
        ["incident", "rash_driving", "hit_and_run", "wrong_way"].includes(
          evt.event_type,
        )
      ) {
        isVisible = showIncidents;
        markerColor = "#dc2626";
        iconSymbol = "🚨";
      }

      if (!isVisible) return;

      const isSelected = selectedEventId === evt.id;

      const eventIcon = L.divIcon({
        className: "custom-event-marker",
        html: `
          <div style="
            width: ${isSelected ? "32px" : "26px"};
            height: ${isSelected ? "32px" : "26px"};
            border-radius: 50%;
            background: ${markerColor};
            border: 2px solid #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: ${isSelected ? "15px" : "12px"};
            cursor: pointer;
            transition: all 0.2s ease;
          ">
            ${iconSymbol}
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([evt.latitude, evt.longitude], {
        icon: eventIcon,
      });
      marker.on("click", () => onSelectEvent(evt));

      marker.bindTooltip(
        `
        <div style="font-size: 11px; padding: 2px; font-family: Inter, system-ui, sans-serif;">
          <b style="color:${markerColor}; text-transform:capitalize;">${evt.event_type.replace(/_/g, " ")}</b> (${Math.round(evt.confidence * 100)}%)
          <br/><span style="color:#a1a1aa;">${evt.description.slice(0, 50)}...</span>
        </div>
      `,
        { sticky: true },
      );

      marker.addTo(markersLayerRef.current!);
    });
  }, [
    buses,
    events,
    selectedEventId,
    showBuses,
    showDefects,
    showCongestion,
    showSafety,
    showIncidents,
    onSelectEvent,
  ]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: height,
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--border-subtle)",
      }}
    >
      {/* Map Container */}
      <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

      {/* Floating Layer Controls */}
      <div
        className="panel map-layer-controls"
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          padding: "12px 14px",
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: "7px",
          boxShadow: "var(--shadow-lg)",
          backdropFilter: "blur(8px)",
        }}
      >
        <button
          onClick={() => setLayersOpen(!layersOpen)}
          aria-expanded={layersOpen}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: "4px",
          }}
        >
          <Layers size={14} color="var(--accent-text)" />
          <span>Map layers</span>
        </button>
        {layersOpen && (
          <div style={{ display: "grid", gap: 8 }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showBuses ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showBuses}
                onChange={(e) => setShowBuses(e.target.checked)}
              />
              <span>Fleet buses ({buses.length})</span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showRoutes ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showRoutes}
                onChange={(e) => setShowRoutes(e.target.checked)}
              />
              <span>Corridor Routes ({routes.length})</span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showDefects
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showDefects}
                onChange={(e) => setShowDefects(e.target.checked)}
              />
              <span style={{ color: "#ea580c" }}>Road Defects & Water</span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showCongestion
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showCongestion}
                onChange={(e) => setShowCongestion(e.target.checked)}
              />
              <span style={{ color: "#db2777" }}>Bottlenecks</span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showSafety ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showSafety}
                onChange={(e) => setShowSafety(e.target.checked)}
              />
              <span style={{ color: "#eab308" }}>Pedestrian Safety</span>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.78rem",
                cursor: "pointer",
                color: showIncidents
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
              }}
            >
              <input
                type="checkbox"
                checked={showIncidents}
                onChange={(e) => setShowIncidents(e.target.checked)}
              />
              <span style={{ color: "#dc2626" }}>Incidents & ANPR</span>
            </label>
          </div>
        )}
      </div>

      {/* Legend at bottom left */}
      <div
        className="panel"
        style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          padding: "6px 12px",
          fontSize: "0.72rem",
          color: "var(--text-secondary)",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span>
          Detections:{" "}
          <b style={{ color: "var(--text-primary)" }}>{events.length}</b>
        </span>
        <span>•</span>
        <span style={{ color: "#22c55e" }}>Recorded observations</span>
      </div>
    </div>
  );
};
export default GisMap;
