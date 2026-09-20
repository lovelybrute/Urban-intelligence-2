import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type CSSProperties,
} from "react";
import { Pause, Play } from "lucide-react";
const MotionContext = createContext({ enabled: true, toggle: () => {} });
export function MotionProvider({ children }: { children: ReactNode }) {
  const [paused, setPaused] = useState(
    () => localStorage.getItem("urban-motion") === "paused",
  );
  const [reduced, setReduced] = useState(
    () =>
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false,
  );
  useEffect(() => {
    const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query?.matches ?? false);
    query?.addEventListener("change", update);
    return () => query?.removeEventListener("change", update);
  }, []);
  const enabled = !paused && !reduced;
  useEffect(() => {
    document.documentElement.dataset.motion = enabled ? "on" : "off";
  }, [enabled]);
  useEffect(() => {
    if (!enabled || window.matchMedia?.("(pointer: coarse)").matches) return;
    let current: HTMLElement | null = null;
    let frame = 0;
    const clear = () => { if(current){ current.style.removeProperty("--tilt-x"); current.style.removeProperty("--tilt-y"); current.style.removeProperty("--glow-x"); current.style.removeProperty("--glow-y"); } current=null; };
    const move = (event: PointerEvent) => {
      const card = (event.target as HTMLElement)?.closest<HTMLElement>(".metric-card, .insight-tile, .journey-card, .model-card, .landing-feature");
      if(card !== current) { cancelAnimationFrame(frame); clear(); current=card; }
      if(!card) return;
      const bounds=card.getBoundingClientRect();
      const x=(event.clientX-bounds.left)/bounds.width;
      const y=(event.clientY-bounds.top)/bounds.height;
      cancelAnimationFrame(frame);
      frame=requestAnimationFrame(()=>{card.style.setProperty("--tilt-x",`${(0.5-y)*7}deg`);card.style.setProperty("--tilt-y",`${(x-0.5)*7}deg`);card.style.setProperty("--glow-x",`${x*100}%`);card.style.setProperty("--glow-y",`${y*100}%`);});
    };
    document.addEventListener("pointermove",move,{passive:true});
    document.addEventListener("pointerleave",clear);
    window.addEventListener("blur",clear);
    return ()=>{cancelAnimationFrame(frame);clear();document.removeEventListener("pointermove",move);document.removeEventListener("pointerleave",clear);window.removeEventListener("blur",clear);};
  }, [enabled]);
  const toggle = () =>
    setPaused((value) => {
      localStorage.setItem("urban-motion", value ? "on" : "paused");
      return !value;
    });
  return (
    <MotionContext.Provider value={{ enabled, toggle }}>
      {children}
    </MotionContext.Provider>
  );
}
export function MotionToggle() {
  const { enabled, toggle } = useContext(MotionContext);
  return (
    <button
      className="motion-toggle btn btn-ghost"
      onClick={toggle}
      aria-label={enabled ? "Pause animations" : "Enable animations"}
      title={enabled ? "Pause animations" : "Enable animations"}
      aria-pressed={enabled}
    >
      {enabled ? <Pause size={15} /> : <Play size={15} />}
    </button>
  );
}
export function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const { enabled } = useContext(MotionContext);
  useEffect(() => {
    if (!enabled || !window.IntersectionObserver) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.08 },
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [enabled]);
  return (
    <div
      ref={ref}
      className={`reveal ${className}`}
      data-visible={visible || !enabled || !window.IntersectionObserver}
      style={{ "--reveal-delay": `${delay}ms` } as CSSProperties}
    >
      {children}
    </div>
  );
}
export function AnimatedNumber({ value }: { value: string | number }) {
  const { enabled } = useContext(MotionContext);
  const target = Number(value);
  const [display, setDisplay] = useState(value);
  const previous = useRef(0);
  useEffect(() => {
    if (!enabled || !Number.isFinite(target)) return;
    const from = previous.current;
    let frame: number;
    const start = performance.now();
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / 850);
      const current = from + (target - from) * (1 - Math.pow(1 - progress, 3));
      setDisplay(
        typeof value === "string" && value.includes(".")
          ? current.toFixed(1)
          : Math.round(current),
      );
      if (progress < 1) frame = requestAnimationFrame(step);
      else previous.current = target;
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value, target, enabled]);
  return (
    <span aria-label={String(value)}>
      <span aria-hidden="true">
        {enabled && Number.isFinite(target) ? display : value}
      </span>
    </span>
  );
}
