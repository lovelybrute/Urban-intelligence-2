import React from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Bus,
  Camera,
  Cpu,
  MapPin,
  ScanLine,
  ShieldCheck,
  Route,
  Layers,
} from "lucide-react";
import { GisMap } from "../components/GisMap";
import { MOCK_BUSES, MOCK_EVENTS, MOCK_ROUTES } from "../services/api";
import "./LandingPage.css";
interface LandingPageProps {
  onOpenDashboard: (tab?: string) => void;
}
export const LandingPage: React.FC<LandingPageProps> = ({
  onOpenDashboard,
}) => (
  <main className="landing-page">
    <nav className="site-nav" aria-label="Main navigation">
      <div className="brand">
        <span className="brand-mark">
          <Layers size={22} />
        </span>
        <span>
          Urban Intelligence<small>MOBILE URBAN SENSING</small>
        </span>
      </div>
      <div className="site-nav-links">
        <a
          href="#capabilities"
          onClick={(e) => {
            e.preventDefault();
            document
              .getElementById("capabilities")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          Capabilities
        </a>
        <span>SIH 26124</span>
        <button
          className="btn btn-primary"
          onClick={() => onOpenDashboard("overview")}
        >
          Open platform <ArrowUpRight size={16} />
        </button>
      </div>
    </nav>
    <section className="landing-hero">
      <div className="landing-copy">
        <div className="landing-kicker">
          <span /> SMART INDIA HACKATHON · PROTOTYPE
        </div>
        <h1>
          Every journey.
          <br />A smarter <em>city.</em>
        </h1>
        <p>
          Turn everyday bus journeys into actionable street intelligence. Detect
          road hazards, understand traffic, and bring critical incidents into
          focus.
        </p>
        <div className="hero-actions">
          <button
            className="btn btn-primary btn-lg"
            onClick={() => onOpenDashboard("overview")}
          >
            Explore command center <ArrowRight size={18} />
          </button>
          <button
            className="btn btn-ghost btn-lg"
            onClick={() => onOpenDashboard("live-map")}
          >
            View sensing map <MapPin size={17} />
          </button>
        </div>
        <div className="prototype-note">
          <ShieldCheck size={16} />
          <span>Working prototype · AI validation in progress</span>
        </div>
      </div>
      <div className="hero-map">
        <div className="hero-map-title">
          <span>
            <MapPin size={15} /> HYDERABAD NETWORK
          </span>
          <span className="badge badge-demo">Sample data</span>
        </div>
        <GisMap
          buses={MOCK_BUSES}
          routes={MOCK_ROUTES}
          events={MOCK_EVENTS}
          onSelectEvent={() => onOpenDashboard("overview")}
          height="400px"
        />
        <div className="hero-map-footer">
          <span>
            <Bus size={17} /> Mobile sensing
          </span>
          <span>
            <ScanLine size={17} /> Geo-tagged detections
          </span>
        </div>
      </div>
    </section>
    <section className="sensing-flow" aria-label="How the platform works">
      {[
        { icon: Camera, title: "Capture", detail: "Bus cameras + GPS" },
        { icon: Cpu, title: "Understand", detail: "Edge video analysis" },
        { icon: MapPin, title: "Locate", detail: "Geo-tagged evidence" },
        {
          icon: ShieldCheck,
          title: "Respond",
          detail: "Authority review + action",
        },
      ].map((s, i) => (
        <div key={s.title}>
          <span className="flow-number">0{i + 1}</span>
          <s.icon size={23} />
          <section>
            <h2>{s.title}</h2>
            <p>{s.detail}</p>
          </section>
          {i < 3 && <ArrowRight className="flow-arrow" size={17} />}
        </div>
      ))}
    </section>
    <section id="capabilities" className="landing-capabilities">
      <div className="capability-intro">
        <div className="eyebrow">ONE FLEET. MULTIPLE PERSPECTIVES.</div>
        <h2>
          Street-level signals.
          <br />
          City-wide understanding.
        </h2>
        <p>
          A shared workspace for transport teams, road maintenance, and incident
          review.
        </p>
      </div>
      <div className="landing-features">
        {[
          {
            icon: Route,
            title: "Road & infrastructure",
            description:
              "Inspect potholes, waterlogging, and damaged infrastructure with location context.",
            tab: "roads",
          },
          {
            icon: Bus,
            title: "Traffic & mobility",
            description:
              "Explore bus routes, congestion, and fleet movement across the city.",
            tab: "traffic",
          },
          {
            icon: ShieldCheck,
            title: "Safety & incidents",
            description:
              "Review pedestrian risks and vehicle incidents with supporting evidence.",
            tab: "incidents",
          },
        ].map((f) => (
          <button
            className="landing-feature"
            key={f.title}
            onClick={() => onOpenDashboard(f.tab)}
          >
            <f.icon size={23} />
            <div>
              <h3>{f.title}</h3>
              <p>{f.description}</p>
            </div>
            <ArrowUpRight size={19} />
          </button>
        ))}
      </div>
    </section>
    <footer className="site-footer">
      <span>Urban Intelligence / SIH 26124</span>
      <span>Public transport. Shared intelligence. Safer streets.</span>
    </footer>
  </main>
);
