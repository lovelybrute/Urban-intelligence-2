import { Car, Gauge, Layers, ArrowUpRight } from "lucide-react";
import type { UrbanEvent, Bus, Route } from "../types";
import { GisMap } from "../components/GisMap";
import { DEMO_MODE } from "../services/api";
import { useRemoteData } from "../hooks/useRemoteData";
import { AnalyticsState } from "../components/AnalyticsState";
interface TrafficStats {
  total_observations: number;
  total_vehicles_counted: number;
  vehicle_composition: Record<string, number>;
  average_speed_kmh: number | null;
}
export const TrafficView = ({
  events,
  buses,
  routes,
}: {
  events: UrbanEvent[];
  buses: Bus[];
  routes: Route[];
}) => {
  const remote = useRemoteData<TrafficStats>("/traffic/stats");
  const congestion = events.filter((e) => e.event_type === "congestion");
  const demoBreakdown = congestion.reduce<Record<string, number>>((all, e) => {
    for (const [kind, value] of Object.entries(
      e.extra_metadata?.vehicle_breakdown || {},
    ))
      if (typeof value === "number") all[kind] = (all[kind] || 0) + value;
    return all;
  }, {});
  const stats = DEMO_MODE
    ? {
        total_observations: congestion.length,
        total_vehicles_counted: congestion.reduce(
          (n, e) => n + (e.extra_metadata?.vehicle_count || 0),
          0,
        ),
        vehicle_composition: demoBreakdown,
        average_speed_kmh: null,
      }
    : remote.data;
  const total = Object.values(stats?.vehicle_composition || {}).reduce(
    (a, b) => a + b,
    0,
  );
  return (
    <div className="analytics-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CITY INTELLIGENCE / MOBILITY</div>
          <h1>
            Traffic, in perspective<span>.</span>
          </h1>
          <p>Vehicle observations and spatial congestion patterns.</p>
        </div>
        <span className="badge badge-accent">
          {DEMO_MODE ? "Sample observations" : "Last 24 hours"}
        </span>
      </div>
      <AnalyticsState {...remote} />
      <div className="summary-grid">
        <article className="insight-tile">
          <Car />
          <span>Vehicle sightings</span>
          <strong>{stats?.total_vehicles_counted ?? "—"}</strong>
          <small>Across observations; not unique vehicles</small>
        </article>
        <article className="insight-tile">
          <Layers />
          <span>Traffic observations</span>
          <strong>{stats?.total_observations ?? "—"}</strong>
          <small>Repeated camera samples included</small>
        </article>
        <article className="insight-tile">
          <Gauge />
          <span>Reported average speed</span>
          <strong>
            {stats?.average_speed_kmh != null
              ? `${stats.average_speed_kmh} km/h`
              : "—"}
          </strong>
          <small>Unavailable without speed measurements</small>
        </article>
      </div>
      <section className="panel analytics-map">
        <div className="section-heading">
          <div>
            <h2>Congestion intensity</h2>
            <span>Intensity represents recorded congestion severity</span>
          </div>
          <span className="badge badge-high">Spatial observations</span>
        </div>
        <GisMap
          buses={buses}
          routes={routes}
          events={events}
          onSelectEvent={() => {}}
          height="430px"
          initialHeatmap
        />
      </section>
      <div className="analytics-columns">
        <section className="panel analytics-section">
          <div className="section-heading">
            <h2>Vehicle composition</h2>
            <Car size={19} />
          </div>
          {Object.entries(stats?.vehicle_composition || {}).map(
            ([name, count], index) => (
              <div className="composition-row" key={name}>
                <div>
                  <span>{name.replaceAll("_", " ")}</span>
                  <strong>{count}</strong>
                </div>
                <div className="composition-track">
                  <span
                    style={{
                      width: `${total ? (count / total) * 100 : 0}%`,
                      background: ["#70dec5", "#7e9eff", "#eab975", "#b1a0f1"][
                        index % 4
                      ],
                    }}
                  />
                </div>
              </div>
            ),
          )}
          {!total && (
            <p className="empty-copy">
              No class breakdown has been recorded. Counts appear when the
              detector supplies vehicle classes.
            </p>
          )}
        </section>
        <section className="panel analytics-section">
          <div className="section-heading">
            <h2>Latest congestion observations</h2>
            <ArrowUpRight size={18} />
          </div>
          {congestion.slice(0, 5).map((e) => (
            <article className="observation-row" key={e.id}>
              <span className={`badge badge-${e.severity}`}>{e.severity}</span>
              <p>{e.description}</p>
              <small>
                Bus {e.bus_id} · {e.latitude.toFixed(4)},{" "}
                {e.longitude.toFixed(4)}
                {e.is_simulated ? " · Simulated" : ""}
              </small>
            </article>
          ))}
          {!congestion.length && (
            <p className="empty-copy">
              No congestion events in the current feed.
            </p>
          )}
        </section>
      </div>
    </div>
  );
};
