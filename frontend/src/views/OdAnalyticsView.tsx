import { ArrowRight, Route as RouteIcon } from "lucide-react";
import type { Route } from "../types";
import { DEMO_MODE } from "../services/api";
import { useRemoteData } from "../hooks/useRemoteData";
import { AnalyticsState } from "../components/AnalyticsState";
export interface Corridor {
  route_id: number;
  route_number: string;
  route_name: string;
  origin: string;
  destination: string;
  observations: number;
  average_minutes: number | null;
  expected_minutes: number;
  delay_minutes: number | null;
  simulated_journeys: number;
}
export const OdAnalyticsView = ({ routes }: { routes: Route[] }) => {
  const remote = useRemoteData<Corridor[]>("/analytics/corridor-journeys");
  const data: Corridor[] = DEMO_MODE
    ? routes.map((r) => ({
        route_id: r.id,
        route_number: r.route_number,
        route_name: r.name,
        origin: r.name.split(" - ")[0],
        destination: r.name.split(" - ")[1] || "Not set",
        observations: 0,
        average_minutes: null,
        expected_minutes: r.expected_duration_minutes,
        delay_minutes: null,
        simulated_journeys: 0,
      }))
    : remote.data || [];
  return (
    <div className="analytics-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">PLANNING / CORRIDOR MOVEMENT</div>
          <h1>
            Where journeys connect<span>.</span>
          </h1>
          <p>
            Bus corridor origin–destination observations from GPS endpoint
            crossings.
          </p>
        </div>
        <RouteIcon size={28} />
      </div>
      <div className="inline-notice">
        This measures bus journeys, not city-wide passenger or private-vehicle
        demand. A completed journey requires sightings near both route
        endpoints.
      </div>
      <AnalyticsState {...remote} />
      <div className="journey-grid">
        {data.map((r) => (
          <article className="panel journey-card" key={r.route_id}>
            <header>
              <span className="badge badge-accent">{r.route_number}</span>
              <span>{r.observations} completed journeys</span>
            </header>
            <div className="journey-endpoints">
              <h2>{r.origin}</h2>
              <ArrowRight size={20} />
              <h2>{r.destination}</h2>
            </div>
            <footer>
              <div>
                <small>Observed average</small>
                <strong>
                  {r.average_minutes === null
                    ? "Awaiting GPS trips"
                    : `${r.average_minutes} min`}
                </strong>
              </div>
              <div>
                <small>Scheduled</small>
                <strong>{r.expected_minutes} min</strong>
              </div>
            </footer>
            {r.simulated_journeys > 0 && (
              <small>
                {r.simulated_journeys} journeys include simulated GPS
              </small>
            )}
          </article>
        ))}
      </div>
      {!data.length && !remote.loading && (
        <p className="empty-copy">No active corridors are available.</p>
      )}
    </div>
  );
};
