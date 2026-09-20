import React, { useEffect, useRef } from "react";
import {
  LayoutDashboard,
  Map,
  Bus,
  AlertOctagon,
  Car,
  Users,
  Camera,
  FileText,
  Cpu,
  Bell,
  Route,
  ChevronLeft,
  ChevronRight,
  X,
  Network,
  Construction,
} from "lucide-react";
interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  alertsCount: number;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  busesCount?: number;
}
const groups = [
  {
    label: "START HERE",
    items: [
      { id: "overview", label: "Overview", icon: LayoutDashboard },
      { id: "live-map", label: "City map", icon: Map },
      { id: "fleet", label: "Your buses", icon: Bus },
    ],
  },
  {
    label: "ROADS & SAFETY",
    items: [
      { id: "roads", label: "Road conditions", icon: AlertOctagon },
      { id: "traffic", label: "Traffic", icon: Car },
      { id: "safety", label: "People & safety", icon: Users },
      { id: "incidents", label: "Vehicles & incidents", icon: Camera },
      { id: "alerts", label: "Alerts", icon: Bell },
    ],
  },
  {
    label: "PLAN & REVIEW",
    items: [
      { id: "routes", label: "Route delays", icon: Route },
      { id: "od-analytics", label: "Bus journeys", icon: Network },
      { id: "infrastructure", label: "Signs & crossings", icon: Construction },
      { id: "reports", label: "Incident reports", icon: FileText },
      { id: "mlops", label: "AI & devices", icon: Cpu },
    ],
  },
];
export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  alertsCount,
  collapsed = false,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
  busesCount = 0,
}) => {
  const drawer = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.activeElement as HTMLElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    drawer.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseMobile?.();
      if (e.key === "Tab") {
        const items =
          drawer.current?.querySelectorAll<HTMLButtonElement>("button");
        if (!items?.length) return;
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [mobileOpen, onCloseMobile]);
  const navigation = (compact: boolean) => (
    <nav aria-label="Operations navigation">
      {groups.map((group) => (
        <section className="nav-group" key={group.label}>
          {!compact && <h2>{group.label}</h2>}
          {group.items.map((item) => (
            <button
              key={item.id}
              title={compact ? item.label : undefined}
              aria-label={item.label}
              aria-current={activeTab === item.id ? "page" : undefined}
              className="nav-item"
              onClick={() => {
                setActiveTab(item.id);
                onCloseMobile?.();
              }}
            >
              <item.icon size={18} />
              {!compact && <span>{item.label}</span>}
              {!compact && item.id === "alerts" && alertsCount > 0 && (
                <b>{alertsCount}</b>
              )}
            </button>
          ))}
        </section>
      ))}
    </nav>
  );
  return (
    <>
      <aside className={`workspace-sidebar ${collapsed ? "is-collapsed" : ""}`}>
        <div className="sidebar-top">
          {!collapsed && <span>YOUR DASHBOARD</span>}
          <button
            className="btn btn-ghost"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
        {navigation(collapsed)}
        {!collapsed && (
          <div className="sidebar-footer">
            <Bus size={18} />
            <div>
              <strong>{busesCount} buses in view</strong>
              <span>Seeing streets through bus cameras</span>
            </div>
          </div>
        )}
      </aside>
      {mobileOpen && (
        <div className="mobile-drawer-overlay" onClick={onCloseMobile}>
          <div
            className="mobile-drawer"
            ref={drawer}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sidebar-top">
              <strong>Navigation</strong>
              <button
                className="btn btn-ghost"
                onClick={onCloseMobile}
                aria-label="Close navigation"
              >
                <X size={21} />
              </button>
            </div>
            {navigation(false)}
          </div>
        </div>
      )}
    </>
  );
};
export default Sidebar;
