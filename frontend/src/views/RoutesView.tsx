import type { Route } from "../types";
import type { Corridor } from "./OdAnalyticsView";
import { DEMO_MODE } from "../services/api";
import { useRemoteData } from "../hooks/useRemoteData";
import { AnalyticsState } from "../components/AnalyticsState";
export const RoutesView = ({ routes }: { routes: Route[] }) => {
  const remote = useRemoteData<Corridor[]>("/analytics/corridor-journeys");
  const rows = DEMO_MODE
    ? routes.map((r) => ({
        route_id: r.id,
        route_name: r.name,
        route_number: r.route_number,
        expected_minutes: r.expected_duration_minutes,
        average_minutes: null,
        delay_minutes: null,
        observations: 0,
      }))
    : remote.data || [];
  return (
    <div className="analytics-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CHECK YOUR BUS ROUTES</div>
          <h1>
            Are buses arriving on time?<span>.</span>
          </h1>
          <p>
            Compare scheduled duration with completed bus journeys from the last
            24 hours.
          </p>
        </div>
      </div>
      <AnalyticsState {...remote} />
      <div className="panel table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Bus route</th>
              <th>Scheduled</th>
              <th>Average trip time</th>
              <th>Difference</th>
              <th>Journeys</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.route_id}>
                <td>
                  <span className="badge badge-accent">{r.route_number}</span>
                  <strong className="route-name">{r.route_name}</strong>
                </td>
                <td>{r.expected_minutes} min</td>
                <td>
                  {r.average_minutes === null
                    ? "Waiting for trip data"
                    : `${r.average_minutes} min`}
                </td>
                <td>
                  {r.delay_minutes === null ? (
                    <span className="badge badge-neutral">Not measured</span>
                  ) : (
                    <span
                      className={`badge badge-${r.delay_minutes > 10 ? "high" : "low"}`}
                    >
                      {r.delay_minutes > 0 ? "+" : ""}
                      {r.delay_minutes} min
                    </span>
                  )}
                </td>
                <td>{r.observations}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="empty-copy">
        Trip times appear after a complete journey is recorded. A minus sign means the trip took less time than planned.
      </p>
    </div>
  );
};
