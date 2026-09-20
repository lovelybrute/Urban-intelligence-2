import { Reveal, MotionToggle } from "../components/Motion";
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
    <div className="ambient-orb ambient-orb-one" aria-hidden="true" />
    <div className="ambient-orb ambient-orb-two" aria-hidden="true" />
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
        <MotionToggle />
        <button
          className="btn btn-primary"
          onClick={() => onOpenDashboard("overview")}
        >
          Open platform <ArrowUpRight size={16} />
        </button>
      </div>
    </nav>
    <section className="landing-hero">
      <div className="landing-copy hero-enter">
        <div className="landing-kicker">
          <span /> SMART INDIA HACKATHON · PROTOTYPE
        </div>
        <h1>
          The city moves.
          <br />
          We connect <em>the dots.</em>
        </h1>
        <p>
          Buses scan the streets while they travel. Our platform spots road problems, traffic, and safety risks, then shows exactly where they happened.
        </p>
        <div className="hero-actions">
          <button
            className="btn btn-primary btn-lg"
            onClick={() => onOpenDashboard("overview")}
          >
            See the live city <ArrowRight size={18} />
          </button>
          <button
            className="btn btn-ghost btn-lg"
            onClick={() => onOpenDashboard("live-map")}
          >
            Open city map <MapPin size={17} />
          </button>
        </div>
        <div className="prototype-note">
          <ShieldCheck size={16} />
          <span>Working prototype · AI validation in progress</span>
        </div>
      </div>
      <div className="hero-map-stage">
        <div className="hero-map-orbit" aria-hidden="true" />
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
        <div className="map-floating-note">
          <span className="note-glyph">
            <ScanLine size={18} />
          </span>
          <div>
            <strong>From a street signal to a city insight</strong>
            <small>Capture · Locate · Review</small>
          </div>
        </div>
      </div>
    </section>
    <Reveal>
      <section className="sensing-flow" aria-label="How the platform works">
        {[
          { icon: Camera, title: "Capture", detail: "Bus cameras + GPS" },
          { icon: Cpu, title: "Understand", detail: "AI checks the video" },
          { icon: MapPin, title: "Locate", detail: "Pins it on the map" },
          {
            icon: ShieldCheck,
            title: "Respond",
            detail: "Teams review + respond",
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
    </Reveal>
    <Reveal>
      <section id="capabilities" className="landing-capabilities">
        <div className="capability-intro">
          <div className="eyebrow">ONE BUS NETWORK. A CLEARER CITY.</div>
          <h2>
            See what is happening.
            <br />
            Know where to act.
          </h2>
          <p>
            One simple place to see road problems, traffic, safety risks, and incidents.
          </p>
        </div>
        <div className="landing-features">
          {[
            {
              icon: Route,
              title: "Road problems",
              description:
                "See potholes, waterlogging, and damaged roads with their exact location.",
              tab: "roads",
            },
            {
              icon: Bus,
              title: "Traffic",
              description:
                "See busy roads, congestion, bus routes, and movement across the city.",
              tab: "traffic",
            },
            {
              icon: ShieldCheck,
              title: "Safety & incidents",
              description:
                "See safety risks and vehicle incidents with location, time, and visual proof.",
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
    </Reveal>
    <footer className="site-footer">
      <span>Urban Intelligence / SIH 26124</span>
      <span>Public transport. Shared intelligence. Safer streets.</span>
    </footer>
  </main>
);
