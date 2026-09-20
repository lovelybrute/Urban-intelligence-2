import { CityScene } from "../components/CityScene";
import { AnimatedNumber } from "../components/Motion";
import React, { useState } from "react";
import type { Bus, UrbanEvent, Alert, RoadSegment, Route } from "../types";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bus as BusIcon,
  ChevronRight,
  MapPin,
  Search,
  ShieldAlert,
} from "lucide-react";
import { GisMap } from "../components/GisMap";
interface OverviewViewProps {
  buses: Bus[];
  events: UrbanEvent[];
  alerts: Alert[];
  roadSegments: RoadSegment[];
  routes: Route[];
  onSelectEvent: (event: UrbanEvent) => void;
  setActiveTab: (tab: string) => void;
}
export const OverviewView: React.FC<OverviewViewProps> = ({
  buses,
  events,
  alerts,
  roadSegments,
  routes,
  onSelectEvent,
  setActiveTab,
}) => {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const active = buses.filter((b) => b.status === "active");
  const critical = alerts.filter(
    (a) => a.category === "critical" && a.status === "active",
  ).length;
  const defects = events.filter((e) =>
    [
      "pothole",
      "crack",
      "damaged_road",
      "waterlogging",
      "road_hazard",
    ].includes(e.event_type),
  ).length;
  const filtered = events
    .filter(
      (e) =>
        (filter !== "priority" || ["critical", "high"].includes(e.severity)) &&
        `${e.event_type.replaceAll("_", " ")} ${e.description} ${e.event_id}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  const metrics = [
    {
      label: "Buses on the road",
      value: active.length,
      detail: `${buses.length} buses in fleet`,
      icon: BusIcon,
      tab: "fleet",
      tone: "blue",
    },
    {
      label: "Road hazards",
      value: defects,
      detail: "Problems in this view",
      icon: AlertTriangle,
      tab: "roads",
      tone: "amber",
    },
    {
      label: "Urgent alerts",
      value: critical,
      detail: "Waiting for a review",
      icon: ShieldAlert,
      tab: "alerts",
      tone: "red",
    },
    {
      label: "Bus routes",
      value: routes.length,
      detail: "See where each journey goes",
      icon: Activity,
      tab: "routes",
      tone: "teal",
    },
  ];
  return (
    <div className="overview">
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR CITY AT A GLANCE</div>
          <h1>
            A clearer view of your city<span>.</span>
          </h1>
          <p>
            See your buses, check road problems, and find what needs attention.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => setActiveTab("reports")}
        >
          Incident reports <ArrowUpRight size={16} />
        </button>
      </div>
      <CityScene busCount={buses.length} eventCount={events.length} onExplore={setActiveTab}/>
      <div className="quick-start"><span>Start here</span>{[{title:"Find a problem",detail:"Explore the map",tab:"live-map"},{title:"See the details",detail:"Open a report",tab:"reports"},{title:"Choose what comes next",detail:"Review alerts",tab:"alerts"}].map((step,i)=><button key={step.tab} onClick={()=>setActiveTab(step.tab)}><b>0{i+1}</b><div><strong>{step.title}</strong><small>{step.detail}</small></div><ArrowUpRight size={16}/></button>)}</div>
      <div className="priority-banner">
        <div className="priority-icon">
          <ShieldAlert size={24} />
        </div>
        <div>
          <span className="eyebrow">NEEDS YOUR ATTENTION</span>
          <h2>
            {critical
              ? `${critical} urgent alerts need attention`
              : "Your city overview is ready"}
          </h2>
          <p>
            {critical
              ? "Open an alert, check the details, and decide what to do next."
              : "Explore your buses, road conditions, and recent reports."}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => setActiveTab("alerts")}
        >
          Review alerts <ArrowUpRight size={16} />
        </button>
      </div>
      <div className="metric-grid">
        {metrics.map((m) => (
          <button
            key={m.label}
            className={`metric-card ${m.tone}`}
            onClick={() => setActiveTab(m.tab)}
          >
            <div className="metric-top">
              <span>{m.label}</span>
              <m.icon size={19} />
            </div>
            <strong>
              <AnimatedNumber value={m.value} />
            </strong>
            <div className="metric-bottom">
              <span>{m.detail}</span>
              <ArrowUpRight size={15} />
            </div>
          </button>
        ))}
      </div>
      <div className="operations-grid">
        <section className="panel map-panel">
          <div className="section-heading">
            <div>
              <h2>See what is happening</h2>
              <span>
                <MapPin size={13} /> Hyderabad, Telangana
              </span>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => setActiveTab("live-map")}
            >
              Expand map <ArrowUpRight size={15} />
            </button>
          </div>
          <GisMap
            roadSegments={roadSegments}
            buses={buses}
            routes={routes}
            events={events}
            onSelectEvent={onSelectEvent}
            height="470px"
          />
          <div className="map-caption">
            <span>{routes.length} routes in view</span>
            <span>Tap a pin to see the details</span>
          </div>
        </section>
        <section className="panel feed-panel">
          <div className="section-heading">
            <div>
              <h2>Recent reports</h2>
              <span>{events.length} recorded events</span>
            </div>
            <span className="badge badge-neutral">Ready to review</span>
          </div>
          <label className="feed-search">
            <Search size={16} />
            <input
              type="search"
              placeholder="Search reports…"
              aria-label="Search reports"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <div className="feed-filters">
            {[
              ["all", "All events"],
              ["priority", "High priority"],
            ].map(([id, label]) => (
              <button
                key={id}
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="event-feed">
            {filtered.length ? (
              filtered.map((e) => (
                <button
                  key={e.id}
                  className="event-card"
                  onClick={() => onSelectEvent(e)}
                >
                  <div className="event-card-top">
                    <span className={`badge badge-${e.severity}`}>
                      {e.severity}
                    </span>
                    <span>
                      {new Date(e.timestamp).toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        timeZone: "Asia/Kolkata",
                      })}{" "}
                      IST
                    </span>
                  </div>
                  <h3>
                    {e.event_type.replaceAll("_", " ")}
                    <ChevronRight size={16} />
                  </h3>
                  <p>{e.description}</p>
                  <div className="event-card-bottom">
                    <span>
                      Bus {e.bus_id} · {Math.round(e.confidence * 100)}%
                      confidence
                    </span>
                    {e.is_simulated && <span>Demo data</span>}
                  </div>
                </button>
              ))
            ) : (
              <div className="empty-state">
                <Search size={25} />
                <h3>No matching reports</h3>
                <p>Try another search or select all events.</p>
              </div>
            )}
          </div>
        </section>
      </div>
      <section className="corridor-section">
        <div className="section-heading">
          <div>
            <h2>Road condition watch</h2>
            <span>Find the roads that need repairs first</span>
          </div>
          <button
            className="btn btn-ghost"
            onClick={() => setActiveTab("roads")}
          >
            View all roads <ArrowUpRight size={16} />
          </button>
        </div>
        <div className="corridor-grid">
          {roadSegments.slice(0, 3).map((r) => (
            <button
              className="corridor-card"
              key={r.id}
              onClick={() => setActiveTab("roads")}
            >
              <div>
                <span>{r.segment_code}</span>
                <span className={`condition-${r.condition}`}>
                  {r.condition}
                </span>
              </div>
              <h3>{r.road_name}</h3>
              <div className="condition-track">
                <span
                  style={{
                    width: `${Math.max(0, Math.min(100, r.condition_score))}%`,
                  }}
                />
              </div>
              <footer>
                <span>{r.defect_count} problems reported</span>
                <strong>{r.condition_score}/100</strong>
              </footer>
            </button>
          ))}
          {!roadSegments.length && (
            <p className="text-secondary">No road condition data available.</p>
          )}
        </div>
      </section>
    </div>
  );
};
export default OverviewView;
