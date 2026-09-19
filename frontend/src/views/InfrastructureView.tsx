import React from 'react';
import { AlertTriangle, Construction, Signpost, Waves } from 'lucide-react';
import { MaintenanceItem, RoadSegment, UrbanEvent } from '../types';

interface Props { events: UrbanEvent[]; roadSegments: RoadSegment[]; maintenanceQueue: MaintenanceItem[]; }
const categories = [
 ['Potholes','pothole'],['Damaged roads','damaged_road'],['Waterlogging','waterlogging'],
 ['Missing dividers','missing_divider'],['Damaged dividers','damaged_divider'],
 ['Missing zebra crossings','missing_zebra'],['Damaged zebra crossings','damaged_zebra'],
 ['Missing signboards','missing_sign'],['Damaged signboards','damaged_sign']
] as const;

export const InfrastructureView: React.FC<Props> = ({events,roadSegments,maintenanceQueue}) => {
 const count=(type:string)=>events.filter(e=>e.event_type===type).length+maintenanceQueue.filter(m=>m.defect_type===type).length;
 const deficient=roadSegments.filter(r=>r.condition==='poor'||r.condition==='critical');
 return <div style={{display:'flex',flexDirection:'column',gap:20}}>
  <div><h2 className="heading-md">Infrastructure Deficiency Intelligence</h2><p style={{color:'var(--text-secondary)',fontSize:'.875rem'}}>Dedicated SIH26124 view for road assets, missing markings, dividers, signboards and waterlogging.</p></div>
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:12}}>
   {categories.map(([label,type],i)=><div className="panel" style={{padding:16}} key={type}>{i===2?<Waves size={18}/>:i>4?<Signpost size={18}/>:<Construction size={18}/>}<b style={{display:'block',fontSize:'1.5rem'}}>{count(type)}</b><span>{label}</span></div>)}
  </div>
  <div className="panel" style={{padding:16}}><h3 className="heading-sm">Priority corridors</h3>{deficient.length===0?<p>No poor/critical road segments in current feed.</p>:deficient.map(r=><div key={r.id} style={{display:'flex',justifyContent:'space-between',padding:'12px 0',borderBottom:'1px solid var(--border-subtle)'}}><span><AlertTriangle size={14} style={{verticalAlign:'middle',marginRight:8}}/>{r.road_name}</span><span className="mono">Health {r.condition_score}/100 · {r.defect_count} defects</span></div>)}</div>
 </div>;
};
export default InfrastructureView;
