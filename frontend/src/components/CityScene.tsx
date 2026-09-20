import { useState, type CSSProperties } from 'react';
import { ArrowUpRight, Bus, ShieldCheck, TriangleAlert } from 'lucide-react';
import { AnimatedNumber } from './Motion';
import './CityScene.css';

const buildings = [[25,24,38,42,38],[83,28,34,36,70],[143,21,43,47,52],[239,26,35,45,86],[298,31,43,35,42],[29,120,36,32,58],[94,119,35,35,30],[152,122,35,42,75],[237,119,34,35,45],[301,115,40,44,65],[36,208,37,31,34],[102,210,36,28,54],[240,204,38,34,37],[301,205,35,32,54]];
const views = [{id:'roads',label:'Roads',icon:TriangleAlert,detail:'Find road problems and see where repairs are needed.'},{id:'traffic',label:'Traffic',icon:Bus,detail:'See bus routes and spots where traffic builds up.'},{id:'safety',label:'Safety',icon:ShieldCheck,detail:'Review nearby risks and help keep people safe.'}];
export function CityScene({busCount,eventCount,onExplore,compact=false}:{busCount:number;eventCount:number;onExplore:(tab:string)=>void;compact?:boolean}){
 const [selected,setSelected]=useState('roads');
 const active=views.find(v=>v.id===selected)!;
 return <section className={`city-experience ${compact?'city-compact':''}`} aria-label="Explore the city dashboard">
  <div className="city-visual" data-topic={selected} aria-hidden="true">
   <div className="city-halo"/><div className="city-world"><div className="city-ground"/>
    <div className="city-road road-one"/><div className="city-road road-two"/><div className="city-road road-three"/>
    {buildings.map(([x,y,w,d,h],i)=><div className="city-building" key={i} style={{left:x,top:y,width:w,height:d,'--height':`${h}px`,'--delay':`${i*35}ms`} as CSSProperties}><i className="building-front"/><i className="building-side"/><i className="building-roof"/></div>)}
    <div className="city-bus bus-one"/><div className="city-bus bus-two"/><div className="city-bus bus-three"/>
    <div className="city-ping ping-one"/><div className="city-ping ping-two"/>
   </div><span className="city-illustration-label">A city in motion · Illustration</span>
  </div>
  <div className="city-content"><div className="city-live-label"><span/> YOUR CITY, CONNECTED</div><h2>Every journey.<br/><em>A better view.</em></h2><p>Bus cameras help us spot road problems, traffic, and safety risks.</p>
   <div className="city-numbers"><div><strong><AnimatedNumber value={busCount}/></strong><span>Buses in this view</span></div><div><strong><AnimatedNumber value={eventCount}/></strong><span>Reports to explore</span></div></div>
   <div className="city-topic-buttons" aria-label="Choose what to explore">{views.map(v=><button key={v.id} aria-pressed={selected===v.id} onClick={()=>setSelected(v.id)}><v.icon size={15}/>{v.label}</button>)}</div>
   <p className="city-topic-detail" aria-live="polite">{active.detail}</p><button className="city-explore" onClick={()=>onExplore(selected)}>Explore {active.label.toLowerCase()} <ArrowUpRight size={16}/></button>
  </div>
 </section>;
}
