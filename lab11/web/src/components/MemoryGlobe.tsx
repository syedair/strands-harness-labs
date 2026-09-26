// The Memory tab: the memory core, what it just recalled, and every note. Expand for the full-screen view.
import { Brain, Maximize2, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { MemoryGraph } from "../api";
import { MemoryCore, type CoreState } from "./MemoryCore";

const FIRE_MS = 6000; // how long a recall keeps firing
const STATES: CoreState[] = ["idle", "thinking", "working", "writing"];

export default function MemoryGlobe({ graph, fired, state }: { graph: MemoryGraph; fired: string[]; state: CoreState }) {
  const [active, setActive] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (fired.length === 0) return;
    setActive(fired);
    const timer = setTimeout(() => setActive([]), FIRE_MS);
    return () => clearTimeout(timer);
  }, [fired]);

  if (graph.nodes.length === 0) {
    return <p className="text-ink-2">No memories yet — tell the assistant something about you.</p>;
  }
  const caption = active.length > 0 && (
    <p className="animate-rise flex items-center gap-2 rounded-full border border-accent/40 bg-bg-1/80 px-3 py-1 text-xs text-accent">
      <Brain size={14} /> Recalled {active.length} {active.length === 1 ? "memory" : "memories"}
    </p>
  );
  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/30">
        {!expanded && <MemoryCore graph={graph} fired={active} state={state} height={300} />}
        <button onClick={() => setExpanded(true)} aria-label="Expand memory core"
                className="press absolute right-3 top-3 rounded-full border border-white/15 p-1.5 text-ink-2 hover:text-ink">
          <Maximize2 size={14} />
        </button>
        <div className="absolute bottom-3 left-3">{caption}</div>
      </div>
      <ul className="space-y-1.5">
        {graph.nodes.map((n) => (
          <li key={n.id} className={`rounded-lg px-3 py-2 transition ${active.includes(n.id) ? "bg-accent/15 text-accent" : "bg-black/20"}`}>
            {n.text}
            {n.hits > 0 && <span className="ml-2 font-mono text-[0.65rem] text-ink-2">recalled {n.hits}×</span>}
          </li>
        ))}
      </ul>

      {expanded && (
        <div className="fixed inset-0 z-50 flex flex-col items-center bg-bg-1/95 backdrop-blur">
          <button onClick={() => setExpanded(false)} aria-label="Close"
                  className="press absolute right-6 top-6 rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink">
            <X size={18} />
          </button>
          <p className="eyebrow mt-10 text-xs">
            Core · {state} · {graph.nodes.length} memories{active.length > 0 ? ` · recalled ${active.length}` : ""}
          </p>
          <div className="w-full flex-1"><MemoryCore graph={graph} fired={active} state={state} height={Math.round(window.innerHeight * 0.66)} floor /></div>
          <h2 className="font-display text-6xl font-light tracking-[0.3em] text-ink">MEMORY</h2>
          <p className="mt-2 font-mono text-xs text-ink-2">Strands Harness memory · recalled before every turn</p>
          <div className="mb-10 mt-4 flex gap-2">
            {STATES.map((s) => (
              <span key={s} className={`rounded-lg border px-3 py-1 font-mono text-xs capitalize ${s === state ? "border-accent/50 bg-accent/10 text-accent" : "border-white/10 text-ink-2"}`}>{s}</span>
            ))}
          </div>
          <div className="absolute bottom-10 left-10">{caption}</div>
        </div>
      )}
    </div>
  );
}
