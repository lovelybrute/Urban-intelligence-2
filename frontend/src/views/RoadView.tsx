import React from 'react';
import { RoadSegment, UrbanEvent, MaintenanceItem } from '../types';
import { AlertOctagon, Wrench, RefreshCw } from 'lucide-react';

interface RoadViewProps {
  roadSegments: RoadSegment[];
  events: UrbanEvent[];
  maintenanceQueue: MaintenanceItem[];
  onSelectEvent: (event: UrbanEvent) => void;
}

export const RoadView: React.FC<RoadViewProps> = ({
  roadSegments,
  events,
  maintenanceQueue,
  onSelectEvent
}) => {
  const defectEvents = events.filter(e =>
    ['pothole', 'crack', 'damaged_road', 'waterlogging', 'damaged_divider', 'missing_sign'].includes(e.event_type)
  );

  const getConditionColor = (cond: string) => {
    switch (cond) {
      case 'good': return '#22c55e';
      case 'fair': return '#eab308';
      case 'poor': return '#ea580c';
      case 'critical': return 'var(--severity-critical)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h2 className="heading-md" style={{ marginBottom: '4px' }}>Road Signs & crossings & Condition Intelligence</h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Continuous road surface assessment, structural crack detection, and prioritized municipal repair dispatch.
        </p>
      </div>

      {/* Road Condition Score Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
        {roadSegments.map((segment) => (
          <div key={segment.id} className="panel" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{segment.segment_code}</span>
              <span
                className="badge"
                style={{
                  backgroundColor: `rgba(255, 255, 255, 0.04)`,
                  color: getConditionColor(segment.condition),
                  border: `1px solid ${getConditionColor(segment.condition)}`,
                  fontSize: '0.6875rem',
                  textTransform: 'capitalize',
                }}
              >
                {segment.condition}
              </span>
            </div>

            <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9375rem', marginBottom: '10px' }}>
              {segment.road_name}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Condition Index:</span>
              <span className="mono" style={{ fontWeight: 700, fontSize: '1.25rem', color: getConditionColor(segment.condition) }}>
                {segment.condition_score}/100
              </span>
            </div>

            <div style={{ width: '100%', height: '5px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden', marginBottom: '10px' }}>
              <div style={{ width: `${segment.condition_score}%`, height: '100%', background: getConditionColor(segment.condition) }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              <span>Defects: <b style={{ color: 'var(--text-primary)' }}>{segment.defect_count}</b></span>
              <span>Bus Passes: <b style={{ color: 'var(--text-primary)' }}>{segment.observation_count}</b></span>
            </div>
          </div>
        ))}
      </div>

      {/* Two Column: Active Road Defect Clusters + Prioritized Maintenance Queue */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }} className="responsive-2col">
        {/* Left: Defect Detections with Cluster Deduplication */}
        <div className="panel" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertOctagon size={16} color="var(--accent-text)" />
              <span>Road problems grouped by location</span>
            </h3>
            <span className="badge badge-neutral" style={{ fontSize: '0.6875rem' }}>{defectEvents.length} Active</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {defectEvents.map((evt) => (
              <div
                key={evt.id}
                onClick={() => onSelectEvent(evt)}
                className="clickable-row"
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, color: evt.severity === 'critical' ? 'var(--severity-critical)' : 'var(--severity-high)', textTransform: 'capitalize', fontSize: '0.8125rem' }}>
                      {evt.event_type.replace(/_/g, ' ')}
                    </span>
                    <span className="badge badge-low" style={{ fontSize: '0.625rem', gap: '4px' }}>
                      <RefreshCw size={10} /> {evt.observation_count || 1} Sightings
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    {evt.description}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                    Geotag: {evt.latitude.toFixed(4)}, {evt.longitude.toFixed(4)}
                  </div>
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
                  <div className="mono" style={{ fontWeight: 700, color: 'var(--accent-text)', fontSize: '1.125rem' }}>
                    {Math.round(evt.confidence * 100)}%
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>AI score</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Prioritized Maintenance Repair Queue */}
        <div className="panel" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wrench size={16} color="#22c55e" />
              <span>Municipal Work Queue</span>
            </h3>
            <span className="badge badge-accent" style={{ fontSize: '0.6875rem' }}>{maintenanceQueue.length} Orders</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {maintenanceQueue.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)' }}>{item.title}</span>
                  <span
                    className="mono"
                    style={{
                      fontWeight: 700,
                      fontSize: '0.8125rem',
                      color: item.priority_score > 85 ? 'var(--severity-critical)' : 'var(--severity-high)',
                    }}
                  >
                    Priority: {Math.round(item.priority_score)}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  {item.description}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  <span>Status: <b style={{ color: 'var(--accent-text)', textTransform: 'uppercase' }}>{item.status.replace('_', ' ')}</b></span>
                  <span>Observation Count: <b style={{ color: 'var(--text-primary)' }}>{item.observation_count}</b></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
export default RoadView;
