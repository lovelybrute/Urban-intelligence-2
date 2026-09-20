import React, { useState, useEffect, useRef } from "react";
import { UrbanEvent } from "../types";
import { apiClient, DEMO_MODE, getEvidence } from "../services/api";
import {
  X,
  Sparkles,
  FileText,
  CornerDownRight,
  Camera,
  Check,
} from "lucide-react";

interface EventModalProps {
  event: UrbanEvent;
  onClose: () => void;
  onStatusChange?: (eventId: number, newStatus: string) => void;
  onOpenReport?: (event: UrbanEvent) => void;
}

export const EventModal: React.FC<EventModalProps> = ({
  event,
  onClose,
  onStatusChange,
  onOpenReport,
}) => {
  const [currentStatus, setCurrentStatus] = useState(event.status);
  const [savingStatus, setSavingStatus] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [evidenceUrl, setEvidenceUrl] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    setEvidenceUrl(null);
    if (event.evidence_path && !DEMO_MODE)
      getEvidence(event.id)
        .then((url) => {
          objectUrl = url;
          if (active) setEvidenceUrl(url);
          else URL.revokeObjectURL(url);
        })
        .catch(() => {});
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [event.id, event.evidence_path]);
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on Escape key & trap focus
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    modalRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Tab") {
        const nodes = modalRef.current?.querySelectorAll<HTMLElement>(
          "button:not([disabled]), a[href], input, select",
        );
        if (nodes?.length) {
          const first = nodes[0],
            last = nodes[nodes.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previous?.focus();
    };
  }, [onClose]);

  const handleAction = async (status: string) => {
    setSavingStatus(true);
    try {
      const result = await apiClient.updateEventStatus(event.id, status);
      setCurrentStatus(status as UrbanEvent["status"]);
      onStatusChange?.(event.id, status);
      setStatusMessage(
        result.simulated
          ? "Demo status updated for this session."
          : "Status saved to the backend.",
      );
    } catch {
      setStatusMessage("Could not save. Your previous status has been kept.");
    } finally {
      setSavingStatus(false);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "critical":
        return <span className="badge badge-critical">Critical Severity</span>;
      case "high":
        return <span className="badge badge-high">High Priority</span>;
      case "medium":
        return <span className="badge badge-medium">Medium</span>;
      default:
        return <span className="badge badge-low">Low</span>;
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="event-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "var(--bg-overlay)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 3000,
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className="panel-elevated animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "680px",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "28px",
          position: "relative",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border-default)",
          boxShadow: "var(--shadow-xl)",
        }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="btn btn-ghost"
          style={{
            position: "absolute",
            top: "18px",
            right: "18px",
            padding: "6px",
            borderRadius: "var(--radius-md)",
          }}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>

        {/* Top Badges */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "12px",
            flexWrap: "wrap",
          }}
        >
          {getSeverityBadge(event.severity)}
          <span className="badge badge-neutral mono">{event.event_id}</span>
          <span className="badge badge-accent mono">
            {currentStatus.replace("_", " ").toUpperCase()}
          </span>
          {event.is_simulated && (
            <span
              className="badge badge-medium"
              style={{ fontSize: "0.6875rem" }}
            >
              Simulated Demo Event
            </span>
          )}
        </div>

        <h2
          id="event-modal-title"
          className="heading-md"
          style={{ marginBottom: "8px" }}
        >
          {event.event_type.replace(/_/g, " ").toUpperCase()}
        </h2>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.9375rem",
            lineHeight: 1.5,
            marginBottom: "24px",
          }}
        >
          {event.description}
        </p>

        {/* Telemetry Metrics Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: "12px",
            marginBottom: "20px",
            backgroundColor: "rgba(255, 255, 255, 0.02)",
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              AI Confidence
            </div>
            <div
              className="mono"
              style={{
                fontSize: "1.125rem",
                fontWeight: 700,
                color: "var(--accent-text)",
                marginTop: "2px",
              }}
            >
              {Math.round(event.confidence * 100)}%
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              GPS Geotag
            </div>
            <div
              className="mono"
              style={{
                fontSize: "0.8125rem",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginTop: "4px",
              }}
            >
              {event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              Detecting Bus
            </div>
            <div
              className="mono"
              style={{
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginTop: "4px",
              }}
            >
              Bus #{event.bus_id}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              Multi-Bus Cluster
            </div>
            <div
              className="mono"
              style={{
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "#22c55e",
                marginTop: "4px",
              }}
            >
              {event.observation_count || 1} Sightings
            </div>
          </div>
        </div>

        {/* AI Reasoning / Audit Trail */}
        <div
          style={{
            backgroundColor: "var(--accent-muted)",
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
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: "var(--accent-text)",
              marginBottom: "10px",
            }}
          >
            <Sparkles size={16} />
            <span>AI Reasoning & Explainability Audit</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {event.ai_reasoning && event.ai_reasoning.length > 0 ? (
              event.ai_reasoning.map((r, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    fontSize: "0.8125rem",
                    color: "var(--text-primary)",
                    lineHeight: 1.5,
                  }}
                >
                  <CornerDownRight
                    size={14}
                    color="var(--accent-text)"
                    style={{ flexShrink: 0, marginTop: "3px" }}
                  />
                  <span>{r}</span>
                </div>
              ))
            ) : (
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                No supporting analysis was supplied for this observation.
              </div>
            )}
          </div>
        </div>

        {/* Evidence Visual Container */}
        <div
          style={{
            height: "190px",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-subtle)",
            marginBottom: "24px",
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {evidenceUrl ? (
            <img
              src={evidenceUrl}
              alt={`Evidence for ${event.event_type}`}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: "20px",
                color: "var(--text-muted)",
              }}
            >
              <Camera
                size={28}
                style={{ margin: "0 auto 8px", opacity: 0.5 }}
              />
              <div
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  color: "var(--text-secondary)",
                }}
              >
                Telemetry Event • No Image Uploaded
              </div>
              <div style={{ fontSize: "0.6875rem", marginTop: "4px" }}>
                No accessible image accompanies this event. Bandwidth savings
                are not measured.
              </div>
            </div>
          )}

          <div
            style={{
              position: "absolute",
              top: "8px",
              left: "8px",
              background: "rgba(9, 9, 11, 0.85)",
              padding: "3px 8px",
              borderRadius: "4px",
              fontSize: "0.6875rem",
              color: "var(--accent-text)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            BUS #{event.bus_id} • CAM_FRONT • 1080p
          </div>

          <div
            style={{
              position: "absolute",
              bottom: "8px",
              right: "8px",
              fontSize: "0.6875rem",
              color: "var(--text-muted)",
              background: "rgba(9, 9, 11, 0.85)",
              padding: "2px 6px",
              borderRadius: "4px",
            }}
          >
            Privacy Sanitized: Bystander plates & faces blurred
          </div>
        </div>

        {/* Feedback message */}
        {statusMessage && (
          <div
            className="animate-fade-in"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 12px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "rgba(37, 99, 235, 0.1)",
              border: "1px solid var(--border-accent)",
              fontSize: "0.75rem",
              color: "var(--accent-text)",
              marginBottom: "16px",
            }}
          >
            <Check size={14} />
            <span>{statusMessage}</span>
          </div>
        )}

        {/* Action Buttons & Status Triage */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={() => handleAction("acknowledged")}
              disabled={savingStatus}
              className={
                currentStatus === "acknowledged"
                  ? "btn btn-primary"
                  : "btn btn-secondary"
              }
              style={{ fontSize: "0.8125rem" }}
            >
              Acknowledge
            </button>
            <button
              onClick={() => handleAction("assigned")}
              disabled={savingStatus}
              className={
                currentStatus === "assigned"
                  ? "btn btn-primary"
                  : "btn btn-secondary"
              }
              style={{ fontSize: "0.8125rem" }}
            >
              Assign Maintenance
            </button>
            <button
              onClick={() => handleAction("false_positive")}
              disabled={savingStatus}
              className={
                currentStatus === "false_positive"
                  ? "btn btn-danger"
                  : "btn btn-secondary"
              }
              style={{ fontSize: "0.8125rem" }}
            >
              Mark False Positive
            </button>
          </div>

          {onOpenReport && (
            <button
              onClick={() => onOpenReport(event)}
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem", gap: "6px" }}
            >
              <FileText size={15} />
              <span>Full Incident Report</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
export default EventModal;
