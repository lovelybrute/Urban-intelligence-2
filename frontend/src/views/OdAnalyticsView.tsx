import React from 'react';
import { Route as RouteIcon, ArrowRight, Clock, Activity } from 'lucide-react';
import { Route } from '../types';

interface Props { routes: Route[]; }

export const OdAnalyticsView: React.FC<Props> = ({ routes }) => {
  const flows = routes.map((r, i) => {
    const [origin, destination] = r.name.split(' - ');
    const observations = 420 + (i * 173);
    const avgMinutes = Math.max(8, Math.round(r.expected_duration_minutes * (0.78 + i * 0.06)));
    return { origin, destination, observations, avgMinutes, route: r.route_number };
  });
  return <div style={{display:'flex',flexDirection:'column',gap:20}}>
    <div><h2 className="heading-md">Origin–Destination Intelligence</h2><p style={{color:'var(--text-secondary)',fontSize:'.875rem'}}>Fleet-derived corridor flows for SIH26124. Demo values are explicitly simulated until production mobility observations are connected.</p></div>
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(190px,1fr))',gap:12}}>
      <div className="panel" style={{padding:16}}><RouteIcon size={18}/><b style={{display:'block',fontSize:'1.4rem'}}>{flows.length}</b><span>Observed OD corridors</span></div>
      <div className="panel" style={{padding:16}}><Activity size={18}/><b style={{display:'block',fontSize:'1.4rem'}}>{flows.reduce((s,f)=>s+f.observations,0).toLocaleString()}</b><span>Demo observations</span></div>
      <div className="panel" style={{padding:16}}><Clock size={18}/><b style={{display:'block',fontSize:'1.4rem'}}>{Math.round(flows.reduce((s,f)=>s+f.avgMinutes,0)/Math.max(flows.length,1))} min</b><span>Mean corridor time</span></div>
    </div>
    <div className="panel" style={{padding:16}}>
      <h3 className="heading-sm" style={{marginBottom:12}}>OD Flow Matrix</h3>
      <div className="table-container"><table style={{width:'100%',borderCollapse:'collapse',fontSize:'.8125rem'}}><thead><tr><th>Route</th><th>Origin</th><th></th><th>Destination</th><th>Observations</th><th>Avg time</th></tr></thead><tbody>
      {flows.map(f=><tr key={f.route} style={{borderTop:'1px solid var(--border-subtle)'}}><td style={{padding:12}}><span className="badge badge-accent">{f.route}</span></td><td>{f.origin}</td><td><ArrowRight size={14}/></td><td>{f.destination}</td><td className="mono">{f.observations}</td><td className="mono">{f.avgMinutes} min</td></tr>)}
      </tbody></table></div>
    </div>
  </div>;
};
export default OdAnalyticsView;
