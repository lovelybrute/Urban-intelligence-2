import React, { useState } from "react";
import { UrbanEvent } from "../types";
import { Printer, Sparkles } from "lucide-react";

interface ReportsViewProps {
  events: UrbanEvent[];
  initialSelectedEvent?: UrbanEvent;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  events,
  initialSelectedEvent,
}) => {
  const [selectedId, setSelectedId] = useState<number | undefined>(
    initialSelectedEvent?.id,
  );
  const selectedEvent =
    events.find((e) => e.id === selectedId) ||
    initialSelectedEvent ||
    events[0] ||
    ({} as UrbanEvent);
  const setSelectedEvent = (event: UrbanEvent) => setSelectedId(event.id);

  const handlePrint = () => {
    window.print();
  };

  const hasPlate = !!selectedEvent.extra_metadata?.plate_number;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h2 className="heading-md" style={{ marginBottom: "4px" }}>
            Incident & Defect Reports
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Prototype reports generated from supplied observations. Review
            evidence before taking action.
          </p>
        </div>

        <button
          onClick={handlePrint}
          className="btn btn-primary"
          style={{ fontSize: "0.8125rem", gap: "6px" }}
        >
          <Printer size={15} />
          <span>Print / Export PDF Dossier</span>
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "300px 1fr",
          gap: "16px",
        }}
        className="responsive-2col"
      >
        {/* Left: Incident Selector */}
        <div
          className="panel"
          style={{ padding: "16px", maxHeight: "720px", overflowY: "auto" }}
        >
          <div
            style={{
              fontSize: "0.72rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              marginBottom: "12px",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Select Incident or Hazard
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {events.map((evt) => {
              const isSelected = evt.id === selectedEvent.id;
              return (
                <div
                  key={evt.id}
                  onClick={() => setSelectedEvent(evt)}
                  className="clickable-row"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelectedEvent(evt);
                    }
                  }}
                  style={{
                    padding: "12px",
                    borderRadius: "var(--radius-md)",
                    cursor: "pointer",
                    background: isSelected
                      ? "var(--accent-muted)"
                      : "rgba(255, 255, 255, 0.02)",
                    border: isSelected
                      ? "1px solid var(--border-accent)"
                      : "1px solid var(--border-subtle)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "4px",
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 600,
                        fontSize: "0.8125rem",
                        color: isSelected
                          ? "var(--text-primary)"
                          : "var(--text-secondary)",
                        textTransform: "capitalize",
                      }}
                    >
                      {evt.event_type.replace(/_/g, " ")}
                    </span>
                    <span
                      className="mono"
                      style={{
                        fontSize: "0.6875rem",
                        color: "var(--accent-text)",
                      }}
                    >
                      {Math.round(evt.confidence * 100)}%
                    </span>
                  </div>
                  <div
                    style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}
                  >
                    {evt.event_id} • Bus #{evt.bus_id}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Printable Formal Incident Dossier */}
        <div
          className="panel printable-report"
          style={{
            padding: "32px",
            background: "var(--bg-card)",
            border: "1px solid var(--border-default)",
          }}
        >
          {/* Official Letterhead */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              borderBottom: "1px solid var(--border-subtle)",
              paddingBottom: "16px",
              marginBottom: "20px",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "0.72rem",
                  letterSpacing: "0.06em",
                  fontWeight: 600,
                  color: "var(--accent-text)",
                  textTransform: "uppercase",
                }}
              >
                URBAN INTELLIGENCE • SIH 26124 PROTOTYPE
              </div>
              <h1
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  marginTop: "4px",
                  letterSpacing: "-0.02em",
                }}
              >
                Mobile Urban Sensing Incident Dossier
              </h1>
              <div
                style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}
              >
                Operator review required · Not an official government document
              </div>
            </div>

            <div style={{ textAlign: "right" }}>
              <div
                className="mono"
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                }}
              >
                {selectedEvent.event_id || "No event selected"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Date: {new Date().toLocaleDateString("en-IN")}
              </div>
            </div>
          </div>

          {/* Dossier Body Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "14px",
              marginBottom: "20px",
            }}
          >
            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                padding: "14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                }}
              >
                INCIDENT CLASSIFICATION
              </div>
              <div
                style={{
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  textTransform: "capitalize",
                }}
              >
                {selectedEvent.event_type?.replace(/_/g, " ")}
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--severity-critical)",
                  marginTop: "4px",
                }}
              >
                Severity: {selectedEvent.severity?.toUpperCase()}
              </div>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                padding: "14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                }}
              >
                GEOSPATIAL COORDINATES
              </div>
              <div
                className="mono"
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                }}
              >
                {selectedEvent.latitude?.toFixed(5)}° N,{" "}
                {selectedEvent.longitude?.toFixed(5)}° E
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  marginTop: "4px",
                }}
              >
                Coordinates supplied by the sensing unit
              </div>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                padding: "14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                }}
              >
                OBSERVING SENSING UNIT
              </div>
              <div
                style={{
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                }}
              >
                Bus #{selectedEvent.bus_id} · Camera{" "}
                {selectedEvent.camera_id ?? "not recorded"}
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--accent-text)",
                  marginTop: "4px",
                }}
              >
                Edge Confidence:{" "}
                {Math.round((selectedEvent.confidence ?? 0) * 100)}%
              </div>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                padding: "14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                }}
              >
                ANPR IDENTIFICATION
              </div>
              <div
                className="mono"
                style={{
                  fontSize: "0.9375rem",
                  fontWeight: 700,
                  color: hasPlate ? "var(--text-primary)" : "var(--text-muted)",
                }}
              >
                {selectedEvent.extra_metadata?.plate_number ||
                  "NO OFFENDER PLATE ASSOCIATED"}
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: hasPlate ? "#22c55e" : "var(--text-muted)",
                  marginTop: "4px",
                }}
              >
                {hasPlate
                  ? "OCR transcription; human verification required"
                  : "Telemetry incident without plate trigger"}
              </div>
            </div>
          </div>

          {/* AI Explainability Statement */}
          <div
            style={{
              background: "var(--accent-muted)",
              border: "1px solid var(--border-accent)",
              borderRadius: "var(--radius-md)",
              padding: "16px",
              marginBottom: "20px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontWeight: 600,
                fontSize: "0.8125rem",
                color: "var(--accent-text)",
                marginBottom: "8px",
              }}
            >
              <Sparkles size={16} />
              <span>Detector notes</span>
            </div>
            <div
              style={{
                fontSize: "0.8125rem",
                color: "var(--text-primary)",
                lineHeight: 1.5,
              }}
            >
              {selectedEvent.ai_reasoning?.map((r, i) => (
                <div key={i} style={{ marginBottom: "4px" }}>
                  • {r}
                </div>
              )) || (
                <div>
                  • No detector reasoning was supplied. Review the source
                  evidence.
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          <div
            style={{
              marginBottom: "24px",
              fontSize: "0.875rem",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            <b style={{ color: "var(--text-primary)" }}>Narrative Summary: </b>
            {selectedEvent.description}
          </div>

          {/* Official Sign-off Block */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-end",
              paddingTop: "20px",
              borderTop: "1px solid var(--border-subtle)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div>
              <div>
                Generated by:{" "}
                <b style={{ color: "var(--text-primary)" }}>
                  Autonomous Edge Sensing System
                </b>
              </div>
              <div>Privacy: Inspect redaction before sharing evidence.</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div
                style={{
                  borderBottom: "1px solid var(--text-muted)",
                  width: "160px",
                  height: "24px",
                  marginBottom: "4px",
                }}
              />
              <div>Authorized Command Officer</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ReportsView;
