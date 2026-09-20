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
        "Road defect detector",
        "Traffic / person detector",
        "Plate detector",
      ].map((name) => ({
        name,
        artifact_present: false,
        status: "Not verified in demo mode",
        validation: null,
        scope: "Connect to the backend to inspect configured artifacts.",
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
          <div className="eyebrow">SYSTEM / MODEL READINESS</div>
          <h1>
            Evidence before confidence<span>.</span>
          </h1>
          <p>
            Model availability and telemetry, with unverified results clearly
            marked.
          </p>
        </div>
        <Cpu size={30} />
      </div>
      <AnalyticsState {...remote} />
      <div className="summary-grid">
        <article className="insight-tile">
          <Video />
          <span>Reporting devices</span>
          <strong>{reporting.length}</strong>
          <small>
            {DEMO_MODE ? "Simulated telemetry" : "Devices with reported FPS"}
          </small>
        </article>
        <article className="insight-tile">
          <Cpu />
          <span>Mean processing rate</span>
          <strong>{fps ? `${fps} FPS` : "—"}</strong>
          <small>
            {DEMO_MODE
              ? "Simulated; not a benchmark"
              : "Unavailable until edge measurements arrive"}
          </small>
        </article>
        <article className="insight-tile">
          <Database />
          <span>Bandwidth reduction</span>
          <strong>Not measured</strong>
          <small>Requires raw-video and transmitted-byte measurements</small>
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
              <dt>Accuracy / mAP</dt>
              <dd>Not verified</dd>
              <dt>Field validation</dt>
              <dd>Pending</dd>
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
