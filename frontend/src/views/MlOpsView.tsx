import { Cpu, CheckCircle2, CircleDashed, Database, Video } from "lucide-react";
import type { Bus } from "../types";
import { DEMO_MODE } from "../services/api";
import { useRemoteData } from "../hooks/useRemoteData";
import { AnalyticsState } from "../components/AnalyticsState";
interface Model {
  name: string;
  artifact_present: boolean;
  status: string;
  validation: null;
  scope: string;
}
export const MlOpsView = ({ buses }: { buses: Bus[] }) => {
  const remote = useRemoteData<Model[]>("/system/models");
  const models = DEMO_MODE
    ? [
        "Road problem detection",
        "Vehicle and person detection",
        "Number plate detection",
      ].map((name) => ({
        name,
        artifact_present: false,
        status: "Not checked in this demo",
        validation: null,
        scope: "Connect your server to check its AI files.",
      }))
    : remote.data || [];
  const reporting = buses.filter((b) => b.edge_fps !== undefined);
  const fps = reporting.length
    ? (
        reporting.reduce((n, b) => n + (b.edge_fps || 0), 0) / reporting.length
      ).toFixed(1)
    : null;
  return (
    <div className="analytics-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CHECK YOUR AI & DEVICES</div>
          <h1>
            See what is ready<span>.</span>
          </h1>
          <p>
            Check your devices and see which AI tools still need testing.
          </p>
        </div>
        <Cpu size={30} />
      </div>
      <AnalyticsState {...remote} />
      <div className="summary-grid">
        <article className="insight-tile">
          <Video />
          <span>Devices sending updates</span>
          <strong>{reporting.length}</strong>
          <small>
            {DEMO_MODE ? "Example device updates" : "Devices reporting their video speed"}
          </small>
        </article>
        <article className="insight-tile">
          <Cpu />
          <span>Video processing speed</span>
          <strong>{fps ? `${fps} FPS` : "—"}</strong>
          <small>
            {DEMO_MODE
              ? "Demo data; not a benchmark"
              : "Unavailable until edge measurements arrive"}
          </small>
        </article>
        <article className="insight-tile">
          <Database />
          <span>Data saved</span>
          <strong>Not measured</strong>
          <small>We need to compare video size with uploaded data first</small>
        </article>
      </div>
      <div className="model-grid">
        {models.map((m) => (
          <article key={m.name} className="panel model-card">
            <div className="model-icon">
              {m.artifact_present ? <CheckCircle2 /> : <CircleDashed />}
            </div>
            <h2>{m.name}</h2>
            <p>{m.status}</p>
            <dl>
              <dt>Detection accuracy</dt>
              <dd>Not verified</dd>
              <dt>Tested on real streets</dt>
              <dd>Not checked yet</dd>
            </dl>
            <small>{m.scope}</small>
          </article>
        ))}
      </div>
      <div className="inline-notice">
        A file being present does not prove that a model loads, recognizes every
        required hazard, or is accurate in real traffic. Upload validated
        results before claiming readiness.
      </div>
    </div>
  );
};
