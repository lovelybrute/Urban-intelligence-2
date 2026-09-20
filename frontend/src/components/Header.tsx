import React, { useEffect, useRef, useState } from "react";
import { Layers, MapPin, Menu, Play, Bell, ChevronDown } from "lucide-react";
import { MotionToggle } from "./Motion";
import { DEMO_MODE } from "../services/api";
interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  activeAlertsCount: number;
  activeBusesCount: number;
  onTriggerDemo: (idx: number) => void | Promise<void>;
  onGoLanding?: () => void;
  onToggleMobileSidebar?: () => void;
}
export const Header: React.FC<HeaderProps> = ({
  setActiveTab,
  activeAlertsCount,
  onTriggerDemo,
  onGoLanding,
  onToggleMobileSidebar,
}) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const menu = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: PointerEvent) => {
      if (!menu.current?.contains(e.target as Node)) setOpen(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", key);
    };
  }, [open]);
  const run = async (idx: number) => {
    setBusy(true);
    setOpen(false);
    setStatus("");
    try {
      await onTriggerDemo(idx);
      setStatus("Example added to the dashboard");
    } catch {
      setStatus("Could not add the example. Try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <header className="workspace-header">
      <div className="header-brand-group">
        <button
          id="mobile-menu-btn"
          className="btn btn-ghost mobile-menu"
          onClick={onToggleMobileSidebar}
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>
        <button
          className="brand"
          onClick={onGoLanding}
          aria-label="Urban Intelligence home"
        >
          <span className="brand-mark">
            <Layers size={21} />
          </span>
          <span>
            Urban Intelligence<small>SIH 26124 · CITY DASHBOARD</small>
          </span>
        </button>
      </div>
      <span className="header-city">
        <MapPin size={15} /> Hyderabad <span>/</span> City dashboard
      </span>
      <div className="header-actions">
        <MotionToggle />
        <button
          className="notification-button"
          onClick={() => setActiveTab("alerts")}
          aria-label={`${activeAlertsCount} critical alerts`}
        >
          <Bell size={19} />
          {activeAlertsCount > 0 && <span>{activeAlertsCount}</span>}
        </button>
        <div ref={menu} className="scenario-control">
          <button
            className="btn btn-primary"
            disabled={busy}
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-controls="scenario-list"
          >
            <Play size={14} />
            {busy ? "Running…" : "Try a demo"}
            <ChevronDown size={14} />
          </button>
          {open && (
            <div className="scenario-menu panel-elevated" id="scenario-list">
              <div className="eyebrow">
                {DEMO_MODE ? "TRY AN EXAMPLE" : "TRY AN EXAMPLE"}
              </div>
              {[
                "Road pothole detection",
                "Same problem, two buses",
                "Busy traffic",
                "Flooded road",
                "People & safety risk",
                "Vehicle number plate",
              ].map((label, idx) => (
                <button key={label} onClick={() => run(idx)}>
                  <span>0{idx + 1}</span>
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <span className="sr-only" role="status">
        {status}
      </span>
    </header>
  );
};
