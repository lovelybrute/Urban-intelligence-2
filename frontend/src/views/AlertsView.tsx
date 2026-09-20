import React, { useState } from "react";
import { Alert } from "../types";
import { apiClient } from "../services/api";
import { Check, ShieldAlert } from "lucide-react";

interface AlertsViewProps {
  alerts: Alert[];
  onUpdate: (id: number, status: Alert["status"]) => void;
}

export const AlertsView: React.FC<AlertsViewProps> = ({ alerts, onUpdate }) => {
  const [busy, setBusy] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const activeAlertsCount = alerts.filter((a) => a.status === "active").length;

  const handleUpdateStatus = async (
    id: number,
    newStatus: "acknowledged" | "resolved",
  ) => {
    if (busy !== null) return;
    setBusy(id);
    try {
      const result = await apiClient.updateAlertStatus(id, newStatus);
      onUpdate(id, newStatus);
      setFeedback(
        result.simulated
          ? "Demo alert updated for this session."
          : "Alert saved to backend.",
      );
    } catch {
      setFeedback("Unable to save. The previous status has been kept.");
    } finally {
      setBusy(null);
    }
    setTimeout(() => setFeedback(null), 3000);
  };

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
            Alerts & Triage Management Center
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Review, acknowledge, and resolve critical road safety hazards,
            defect alerts, and transit incidents.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {feedback && (
            <span
              className="badge badge-accent animate-fade-in"
              style={{
                fontSize: "0.75rem",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <Check size={12} /> {feedback}
            </span>
          )}
          <span
            className="badge badge-critical"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <ShieldAlert size={13} />
            <span>{activeAlertsCount} Active System Alerts</span>
          </span>
        </div>
      </div>

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <div className="table-container">
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "left",
              fontSize: "0.8125rem",
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-subtle)",
                  background: "rgba(255, 255, 255, 0.02)",
                  color: "var(--text-muted)",
                }}
              >
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Severity
                </th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Alert ID
                </th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Title & Description
                </th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Detected Time
                </th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Current Status
                </th>
                <th style={{ padding: "12px 16px", fontWeight: 600 }}>
                  Operator Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alt) => (
                <tr
                  key={alt.id}
                  className="clickable-row"
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td style={{ padding: "14px 16px" }}>
                    <span
                      className={`badge badge-${alt.category}`}
                      style={{ textTransform: "capitalize" }}
                    >
                      {alt.category}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <span
                      className="mono"
                      style={{ fontWeight: 600, color: "var(--text-primary)" }}
                    >
                      {alt.alert_id}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px", maxWidth: "380px" }}>
                    <div
                      style={{
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        marginBottom: "2px",
                      }}
                    >
                      {alt.title}
                    </div>
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {alt.description}
                    </div>
                  </td>
                  <td
                    style={{ padding: "14px 16px", color: "var(--text-muted)" }}
                  >
                    <div className="mono" style={{ fontSize: "0.75rem" }}>
                      {new Date(alt.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <span
                      className={`badge ${
                        alt.status === "resolved"
                          ? "badge-low"
                          : alt.status === "acknowledged"
                            ? "badge-accent"
                            : "badge-critical"
                      }`}
                      style={{
                        fontSize: "0.6875rem",
                        textTransform: "capitalize",
                      }}
                    >
                      {alt.status}
                    </span>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", gap: "8px" }}>
                      {alt.status !== "acknowledged" &&
                        alt.status !== "resolved" && (
                          <button
                            disabled={busy !== null}
                            onClick={() =>
                              handleUpdateStatus(alt.id, "acknowledged")
                            }
                            className="btn btn-secondary"
                            style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                          >
                            Acknowledge
                          </button>
                        )}
                      {alt.status !== "resolved" && (
                        <button
                          disabled={busy !== null}
                          onClick={() => handleUpdateStatus(alt.id, "resolved")}
                          className="btn btn-secondary"
                          style={{
                            fontSize: "0.75rem",
                            padding: "4px 10px",
                            color: "#22c55e",
                          }}
                        >
                          Resolve
                        </button>
                      )}
                      {alt.status === "resolved" && (
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          Resolved
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default AlertsView;
