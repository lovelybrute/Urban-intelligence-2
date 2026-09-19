import React, { useState, useEffect, useCallback } from "react";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { GisMap } from "./components/GisMap";
import { EventModal } from "./components/EventModal";
import { LandingPage } from "./views/LandingPage";

// Views
import { OverviewView } from "./views/OverviewView";
import { FleetView } from "./views/FleetView";
import { RoadView } from "./views/RoadView";
import { TrafficView } from "./views/TrafficView";
import { SafetyView } from "./views/SafetyView";
import { IncidentsView } from "./views/IncidentsView";
import { AlertsView } from "./views/AlertsView";
import { RoutesView } from "./views/RoutesView";
import { ReportsView } from "./views/ReportsView";
import { MlOpsView } from "./views/MlOpsView";
import { OdAnalyticsView } from "./views/OdAnalyticsView";
import { InfrastructureView } from "./views/InfrastructureView";

import {
  apiClient,
  DEMO_MODE,
  MOCK_BUSES,
  MOCK_ROUTES,
  MOCK_EVENTS,
  MOCK_ALERTS,
  MOCK_ROAD_SEGMENTS,
  MOCK_MAINTENANCE,
} from "./services/api";
import {
  Bus,
  Route,
  UrbanEvent,
  Alert,
  RoadSegment,
  MaintenanceItem,
} from "./types";
import { AlertCircle, RefreshCw } from "lucide-react";

const getInitialViewMode = (): "landing" | "dashboard" => {
  const hash =
    typeof window !== "undefined" ? window.location.hash.replace(/^#/, "") : "";
  return !hash || hash === "landing" ? "landing" : "dashboard";
};

const getInitialTab = (): string => {
  const hash =
    typeof window !== "undefined" ? window.location.hash.replace(/^#/, "") : "";
  const validTabs = [
    "overview",
    "live-map",
    "fleet",
    "roads",
    "traffic",
    "safety",
    "incidents",
    "alerts",
    "routes",
    "od-analytics",
    "infrastructure",
    "reports",
    "mlops",
  ];
  return validTabs.includes(hash) ? hash : "overview";
};

export const App: React.FC = () => {
  // Navigation & View Mode
  const [viewMode, setViewMode] = useState<"landing" | "dashboard">(
    getInitialViewMode,
  );
  const [activeTab, setActiveTab] = useState<string>(getInitialTab);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);

  // Data state
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(false);
  const [buses, setBuses] = useState<Bus[]>(DEMO_MODE ? MOCK_BUSES : []);
  const [routes, setRoutes] = useState<Route[]>(DEMO_MODE ? MOCK_ROUTES : []);
  const [events, setEvents] = useState<UrbanEvent[]>(
    DEMO_MODE ? MOCK_EVENTS : [],
  );
  const [alerts, setAlerts] = useState<Alert[]>(DEMO_MODE ? MOCK_ALERTS : []);
  const [roadSegments, setRoadSegments] = useState<RoadSegment[]>(
    DEMO_MODE ? MOCK_ROAD_SEGMENTS : [],
  );
  const [maintenanceQueue, setMaintenanceQueue] = useState<MaintenanceItem[]>(
    DEMO_MODE ? MOCK_MAINTENANCE : [],
  );

  const [selectedEvent, setSelectedEvent] = useState<UrbanEvent | null>(null);
  const [reportEvent, setReportEvent] = useState<UrbanEvent | null>(null);

  // Sync with URL Hash for Browser Back/Forward support
  useEffect(() => {
    const handlePopState = () => {
      const hash = window.location.hash.replace(/^#/, "");
      if (!hash || hash === "landing") {
        setViewMode("landing");
      } else {
        setViewMode("dashboard");
        const validTabs = [
          "overview",
          "live-map",
          "fleet",
          "roads",
          "traffic",
          "safety",
          "incidents",
          "alerts",
          "routes",
          "od-analytics",
          "infrastructure",
          "reports",
          "mlops",
        ];
        if (validTabs.includes(hash)) {
          setActiveTab(hash);
        }
      }
    };

    window.addEventListener("popstate", handlePopState);
    window.addEventListener("hashchange", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("hashchange", handlePopState);
    };
  }, []);

  const navigateToTab = (tab: string) => {
    setActiveTab(tab);
    setViewMode("dashboard");
    window.history.pushState(null, "", `#${tab}`);
  };

  const navigateToLanding = () => {
    setViewMode("landing");
    window.history.pushState(null, "", "#landing");
  };

  // Initial data fetch
  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [b, r, e, a, roads, maint] = await Promise.all([
        apiClient.getBuses(),
        apiClient.getRoutes(),
        apiClient.getEvents(),
        apiClient.getAlerts(),
        apiClient.getRoadSegments(),
        apiClient.getMaintenanceQueue(),
      ]);
      setBuses(b);
      setRoutes(r);
      setEvents(e);
      setAlerts(a);
      setRoadSegments(roads);
      setMaintenanceQueue(maint);
      setLoadError("");
    } catch {
      setLoadError(
        "Unable to load backend telemetry data. Check connection and click retry.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Live simulation ticker: updates bus GPS coordinates smoothly along their routes
  useEffect(() => {
    if (!DEMO_MODE) return;
    const interval = setInterval(() => {
      setBuses((prevBuses) =>
        prevBuses.map((bus) => {
          const speed = Math.max(
            12,
            Math.min(50, Math.round(bus.speed + (Math.random() * 4 - 2))),
          );
          const latDelta = (Math.random() - 0.5) * 0.0004;
          const lngDelta = (Math.random() - 0.5) * 0.0004;
          return {
            ...bus,
            speed,
            current_latitude: Number(
              (bus.current_latitude + latDelta).toFixed(5),
            ),
            current_longitude: Number(
              (bus.current_longitude + lngDelta).toFixed(5),
            ),
            edge_fps: Number((21.0 + Math.random() * 2.5).toFixed(1)),
          };
        }),
      );
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  const closeMobileSidebar = useCallback(() => setMobileSidebarOpen(false), []);

  // Trigger SIH Demonstration Scenario
  const handleTriggerDemo = async (scenarioIdx: number) => {
    try {
      await apiClient.triggerDemoScenario(scenarioIdx);
      if (!DEMO_MODE) {
        const [b, r, e, a, roads, maint] = await Promise.all([
          apiClient.getBuses(),
          apiClient.getRoutes(),
          apiClient.getEvents(),
          apiClient.getAlerts(),
          apiClient.getRoadSegments(),
          apiClient.getMaintenanceQueue(),
        ]);
        setBuses(b);
        setRoutes(r);
        setEvents(e);
        setAlerts(a);
        setRoadSegments(roads);
        setMaintenanceQueue(maint);
      }
      setLoadError("");
    } catch {
      setLoadError(
        "Unable to trigger the scenario. Check the backend connection and retry.",
      );
      throw new Error("Scenario failed");
    }

    if (DEMO_MODE && scenarioIdx !== 1) {
      const types = [
        "pothole",
        "pothole",
        "congestion",
        "waterlogging",
        "pedestrian_risk",
        "hit_and_run",
      ];
      const sample = MOCK_EVENTS.find(
        (event) => event.event_type === types[scenarioIdx],
      );
      if (sample) {
        const id = Date.now();
        const event = {
          ...sample,
          id,
          event_id: `DEMO_${id}`,
          timestamp: new Date().toISOString(),
          is_simulated: true,
          status: "detected" as const,
        };
        setEvents((previous) => [event, ...previous]);
        setAlerts((previous) => [
          {
            id,
            alert_id: `DEMO_ALERT_${id}`,
            category: event.severity,
            title: event.event_type.replaceAll("_", " "),
            description: event.description,
            event_id: id,
            status: "active",
            created_at: event.timestamp,
          },
          ...previous,
        ]);
      }
    }

    // If scenario 1 (Spatial Deduplication): increment observation count of the Nampally pothole
    if (DEMO_MODE && scenarioIdx === 1) {
      setEvents((prev) =>
        prev.map((evt) =>
          evt.event_type === "pothole"
            ? {
                ...evt,
                confidence: 0.96,
                observation_count: (evt.observation_count || 1) + 1,
                ai_reasoning: [
                  ...(evt.ai_reasoning || []),
                  "Corroborating sighting: Re-identified by Bus TS09-3207. Confidence reinforced to 96%.",
                ],
              }
            : evt,
        ),
      );
    }
  };

  const handleOpenReport = (evt: UrbanEvent) => {
    setSelectedEvent(null);
    setReportEvent(evt);
    navigateToTab("reports");
  };

  // Render Landing Page
  if (viewMode === "landing") {
    return (
      <LandingPage
        onOpenDashboard={(tab: string = "overview") => {
          navigateToTab(tab || "overview");
        }}
      />
    );
  }

  const activeCriticalAlerts = alerts.filter(
    (a) => a.status === "active" && a.category === "critical",
  ).length;
  const totalActiveAlerts = alerts.filter((a) => a.status === "active").length;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "var(--bg-root)",
      }}
    >
      <div className="mode-banner">
        <span>
          {DEMO_MODE
            ? "SIMULATION MODE · Sample Hyderabad telemetry. No live emergency dispatch."
            : loadError
              ? "BACKEND UNAVAILABLE · Connection needs attention."
              : loading
                ? "BACKEND MODE · Loading telemetry…"
                : "BACKEND MODE · Latest retrieved telemetry."}
        </span>
        <button onClick={navigateToLanding}>About the prototype ↗</button>
      </div>

      {/* Load error notification */}
      {loadError && (
        <div
          role="alert"
          style={{
            margin: "12px 16px 0",
            padding: "10px 16px",
            borderRadius: "var(--radius-md)",
            background: "var(--severity-critical-muted)",
            border: "1px solid rgba(220, 38, 38, 0.4)",
            color: "#fca5a5",
            fontSize: "0.8125rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertCircle size={16} />
            <span>{loadError}</span>
          </div>
          <button
            onClick={loadData}
            className="btn btn-secondary"
            style={{ fontSize: "0.75rem", padding: "4px 10px", gap: "4px" }}
          >
            <RefreshCw size={12} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={navigateToTab}
        activeAlertsCount={activeCriticalAlerts}
        activeBusesCount={buses.length}
        onTriggerDemo={handleTriggerDemo}
        onGoLanding={navigateToLanding}
        onToggleMobileSidebar={() => setMobileSidebarOpen((prev) => !prev)}
      />

      {/* Main Dashboard Layout */}
      <div className="workspace-layout">
        {/* Navigation Sidebar */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={navigateToTab}
          alertsCount={totalActiveAlerts}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
          mobileOpen={mobileSidebarOpen}
          onCloseMobile={closeMobileSidebar}
          busesCount={buses.length}
        />

        {/* View Content Area */}
        <main className="workspace-main" id="main-content">
          {loading && (
            <div
              style={{
                padding: "40px",
                textAlign: "center",
                color: "var(--text-secondary)",
              }}
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  border: "3px solid var(--border-default)",
                  borderTopColor: "var(--accent)",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                  margin: "0 auto 12px",
                }}
              />
              <div style={{ fontSize: "0.875rem" }}>
                Synchronizing edge telemetry stream...
              </div>
            </div>
          )}

          {!loading && (
            <>
              {activeTab === "overview" && (
                <OverviewView
                  buses={buses}
                  events={events}
                  alerts={alerts}
                  roadSegments={roadSegments}
                  routes={routes}
                  onSelectEvent={(evt) => setSelectedEvent(evt)}
                  setActiveTab={navigateToTab}
                />
              )}

              {activeTab === "live-map" && (
                <div className="panel" style={{ padding: "16px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "14px",
                    }}
                  >
                    <h2 className="heading-sm">
                      Fullscreen GIS Situational Operations Map
                    </h2>
                    <span className="badge badge-accent">
                      Interactive Leaflet GIS
                    </span>
                  </div>
                  <GisMap
                    buses={buses}
                    routes={routes}
                    events={events}
                    onSelectEvent={(evt) => setSelectedEvent(evt)}
                    height="calc(100vh - 190px)"
                  />
                </div>
              )}

              {activeTab === "fleet" && (
                <FleetView buses={buses} routes={routes} />
              )}

              {activeTab === "roads" && (
                <RoadView
                  roadSegments={roadSegments}
                  events={events}
                  maintenanceQueue={maintenanceQueue}
                  onSelectEvent={(evt) => setSelectedEvent(evt)}
                />
              )}

              {activeTab === "traffic" && <TrafficView events={events} />}

              {activeTab === "safety" && (
                <SafetyView
                  events={events}
                  onSelectEvent={(evt) => setSelectedEvent(evt)}
                />
              )}

              {activeTab === "incidents" && (
                <IncidentsView
                  events={events}
                  onSelectEvent={(evt) => setSelectedEvent(evt)}
                  onOpenReport={handleOpenReport}
                />
              )}

              {activeTab === "alerts" && <AlertsView alerts={alerts} />}

              {activeTab === "routes" && <RoutesView routes={routes} />}

              {activeTab === "od-analytics" && (
                <OdAnalyticsView routes={routes} />
              )}

              {activeTab === "infrastructure" && (
                <InfrastructureView
                  events={events}
                  roadSegments={roadSegments}
                  maintenanceQueue={maintenanceQueue}
                />
              )}

              {activeTab === "reports" && (
                <ReportsView
                  events={events}
                  initialSelectedEvent={reportEvent || events[0]}
                />
              )}

              {activeTab === "mlops" && <MlOpsView />}
            </>
          )}
        </main>
      </div>

      {/* Detail Event Modal */}
      {selectedEvent && (
        <EventModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onStatusChange={(id, newStatus) => {
            setEvents((prev) =>
              prev.map((e) =>
                e.id === id ? { ...e, status: newStatus as any } : e,
              ),
            );
          }}
          onOpenReport={handleOpenReport}
        />
      )}
    </div>
  );
};

export default App;
