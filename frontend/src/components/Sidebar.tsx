import React from 'react';
import {
  LayoutDashboard, Map, Bus, AlertOctagon, Car, Users,
  Camera, FileText, Cpu, Bell, Route, ChevronLeft, ChevronRight, X, Network, Construction
} from 'lucide-react';

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

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  alertsCount,
  collapsed = false,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
  busesCount = 10,
}) => {
  const menuItems = [
    { id: 'overview', label: 'Command Center', icon: LayoutDashboard },
    { id: 'live-map', label: 'Live GIS Map', icon: Map },
    { id: 'fleet', label: 'Bus Fleet', icon: Bus },
    { id: 'roads', label: 'Road Quality', icon: AlertOctagon },
    { id: 'traffic', label: 'Traffic & Flow', icon: Car },
    { id: 'safety', label: 'Pedestrian Safety', icon: Users },
    { id: 'incidents', label: 'Incidents & ANPR', icon: Camera },
    { id: 'alerts', label: 'Alerts Center', icon: Bell, badge: alertsCount },
    { id: 'routes', label: 'Route Delays', icon: Route },
    { id: 'od-analytics', label: 'OD Analytics', icon: Network },
    { id: 'infrastructure', label: 'Infrastructure', icon: Construction },
    { id: 'reports', label: 'Incident Reports', icon: FileText },
    { id: 'mlops', label: 'MLOps Health', icon: Cpu },
  ];

  const handleItemClick = (id: string) => {
    setActiveTab(id);
    if (onCloseMobile) onCloseMobile();
  };

  const sidebarContent = (
    <aside
      className="panel"
      style={{
        width: collapsed ? '68px' : '230px',
        padding: '14px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        height: 'calc(100vh - 96px)',
        position: 'sticky',
        top: '84px',
        flexShrink: 0,
        transition: 'width var(--transition-base)',
        overflow: 'hidden',
      }}
      aria-label="Operations Navigation"
    >
      {/* Header with collapse button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: '4px 8px 10px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '6px',
        }}
      >
        {!collapsed && (
          <span style={{ fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
            Modules
          </span>
        )}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="btn btn-ghost"
            style={{ padding: '4px', borderRadius: '4px' }}
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '3px', overflowY: 'auto', flex: 1 }}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleItemClick(item.id)}
              title={collapsed ? item.label : undefined}
              aria-current={isActive ? 'page' : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '10px 0' : '9px 12px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8125rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-muted)' : 'transparent',
                border: isActive ? '1px solid var(--border-accent)' : '1px solid transparent',
                transition: 'all var(--transition-fast)',
                textAlign: 'left',
                cursor: 'pointer',
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Icon size={17} color={isActive ? 'var(--accent-text)' : 'currentColor'} />
                {!collapsed && <span>{item.label}</span>}
              </div>

              {!collapsed && item.badge !== undefined && item.badge > 0 && (
                <span className="badge badge-critical" style={{ padding: '1px 6px', fontSize: '0.625rem' }}>
                  {item.badge}
                </span>
              )}

              {collapsed && item.badge !== undefined && item.badge > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '4px',
                    right: '8px',
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    background: 'var(--severity-critical)',
                  }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* System Health Footer */}
      {!collapsed && (
        <div
          style={{
            marginTop: 'auto',
            padding: '10px 12px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Camera Telemetry</span>
            <span style={{ color: '#22c55e', fontWeight: 600 }}>{busesCount * 4} HD Cams</span>
          </div>
          <div
            style={{
              width: '100%',
              height: '3px',
              borderRadius: '2px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: '96%',
                height: '100%',
                backgroundColor: '#22c55e',
                borderRadius: '2px',
              }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            <span>Edge filtering</span>
            <span className="mono" style={{ color: 'var(--accent-text)' }}>measurement pending</span>
          </div>
        </div>
      )}
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hide-mobile" style={{ marginLeft: '16px' }}>
        {sidebarContent}
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'var(--bg-overlay)',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            zIndex: 2500,
            display: 'flex',
          }}
          onClick={onCloseMobile}
        >
          <div
            style={{
              width: '260px',
              height: '100%',
              backgroundColor: 'var(--bg-card)',
              borderRight: '1px solid var(--border-default)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: 'var(--shadow-xl)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 700 }}>Navigation</span>
              <button onClick={onCloseMobile} className="btn btn-ghost" style={{ padding: '6px' }} aria-label="Close menu">
                <X size={18} />
              </button>
            </div>
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
export default Sidebar;
