import React, { StrictMode, Component, ReactNode, ErrorInfo } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { MotionProvider } from "./components/Motion";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in application:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            background: "#09090b",
            color: "#fafafa",
            padding: "40px 24px",
            fontFamily: "Inter, system-ui, sans-serif",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              maxWidth: "640px",
              width: "100%",
              background: "#18181b",
              border: "1px solid rgba(220, 38, 38, 0.4)",
              borderRadius: "12px",
              padding: "28px",
              boxShadow: "0 16px 40px rgba(0,0,0,0.6)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "14px",
              }}
            >
              <span
                style={{
                  background: "rgba(220, 38, 38, 0.15)",
                  color: "#dc2626",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                }}
              >
                RENDER ERROR
              </span>
              <h2 style={{ fontSize: "1.125rem", fontWeight: 700, margin: 0 }}>
                Application Notice
              </h2>
            </div>
            <p
              style={{
                fontSize: "0.875rem",
                color: "#a1a1aa",
                marginBottom: "16px",
                lineHeight: 1.5,
              }}
            >
              The application encountered a render issue. You can reload or
              reset to the landing page.
            </p>
            <pre
              style={{
                background: "#111113",
                padding: "12px",
                borderRadius: "6px",
                fontSize: "0.78rem",
                color: "#f87171",
                overflowX: "auto",
                marginBottom: "20px",
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {this.state.error?.message || "Unknown error"}
            </pre>
            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  background: "#2563eb",
                  color: "#fff",
                  border: "none",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Reload Platform
              </button>
              <button
                onClick={() => {
                  window.location.hash = "#landing";
                  window.location.reload();
                }}
                style={{
                  background: "#27272a",
                  color: "#fafafa",
                  border: "1px solid rgba(255,255,255,0.1)",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Return to Landing Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <MotionProvider>
        <App />
      </MotionProvider>
    </ErrorBoundary>
  </StrictMode>,
);
