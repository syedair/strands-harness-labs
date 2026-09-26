// The Memory tab: the memory core, what was just recalled (and why), and every note, newest first.
import { Brain, Eraser, Maximize2, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { MemoryGraph } from "../api";
import { ConfirmButton } from "./ConfirmButton";
import { MemoryCore, type CoreState } from "./MemoryCore";
import { memoriesOnly, recallLabel, showingFor, withGhosts, type Burst, type Ghosts } from "../globe";

const STATES: CoreState[] = ["idle", "thinking", "working", "writing"];
export type Recall = { query: string; ids: string[]; scores: number[] };

type Props = {
  graph: MemoryGraph; fired: Burst; stored: Burst; forgot: Ghosts; recall: Recall | null; state: CoreState;
  visible?: boolean; // false while another tab or page is showing
  onForget: (id: string) => void;
  onForgetAll: () => void;
};

function useForAWhile(burst: Burst) {
  const [active, setActive] = useState<string[]>([]);
  useEffect(() => {
    const left = showingFor(burst, Date.now());
    if (left === 0) return;
    setActive(burst.ids);
    const timer = setTimeout(() => setActive([]), left);
    return () => clearTimeout(timer);
  }, [burst]);
  return active;
}

export default function MemoryGlobe({ graph, fired, stored, forgot, recall, state, onForget, onForgetAll, visible = true }: Props) {
  const firing = useForAWhile(fired);
  const saving = useForAWhile(stored);
  const forgetting = useForAWhile(forgot);
  const pictured = withGhosts(graph, forgot.nodes, forgetting); // forgotten notes dissolve before they disappear
  const [expanded, setExpanded] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  if (pictured.nodes.length === 0) {
    return <p className="text-ink-2">No memories yet — tell the assistant something about you.</p>;
  }
  const caption = (firing.length > 0 || saving.length > 0 || forgetting.length > 0) && (
    <div className="flex flex-col gap-1.5">
      {firing.length > 0 && (
        <p className="animate-rise flex items-center gap-2 rounded-full border border-accent/40 bg-bg-1/80 px-3 py-1 text-xs text-accent">
          <Brain size={14} /> Recalled {recallLabel(firing)}
        </p>
      )}
      {saving.length > 0 && (
        <p className="animate-rise flex items-center gap-2 rounded-full border border-violet/50 bg-bg-1/80 px-3 py-1 text-xs text-violet">
          <Brain size={14} /> Storing a new memory
        </p>
      )}
      {forgetting.length > 0 && (
        <p className="animate-rise flex items-center gap-2 rounded-full border border-warn/50 bg-bg-1/80 px-3 py-1 text-xs text-warn">
          <Eraser size={14} /> Forgetting {forgetting.length} {forgetting.length === 1 ? "memory" : "memories"}
        </p>
      )}
    </div>
  );
  const core = (height: number, close = false) => (
    <MemoryCore graph={pictured} fired={firing} stored={saving} forgotten={forgetting} state={state} height={height} close={close} paused={!visible} />
  );
  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/30">
        {!expanded && core(300)}
        <button onClick={() => setExpanded(true)} aria-label="Expand memory core"
                className="press absolute right-3 top-3 rounded-full border border-white/15 p-1.5 text-ink-2 hover:text-ink">
          <Maximize2 size={14} />
        </button>
        <div className="absolute bottom-3 left-3">{caption}</div>
      </div>

      {recall && (
        <div className="rounded-xl border border-white/10 px-3 py-2 text-xs">
          <p className="eyebrow text-[0.6rem] text-ink-2">Last recall</p>
          <p className="mt-1 text-ink-2">Searched for <span className="text-ink">"{recall.query}"</span></p>
          {graph.knowledge && (
        <p className="text-xs text-ink-2">
          Also recalls from <span className="font-mono text-ink">{graph.knowledge.dir}</span> · {graph.knowledge.sections} sections,
          read-only (the pale outer shell)
        </p>
      )}
      <ul className="mt-1 space-y-0.5 font-mono">
            {recall.ids.map((id, i) => (
              <li key={id} className="flex justify-between gap-3">
                <span className="truncate">{id.replace(/\.md$/, "")}</span>
                <span className="text-accent">{recall.scores[i]?.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ul className="space-y-1.5">
        {memoriesOnly(graph).map((n) => (
          <li key={n.id} className={`group relative rounded-lg px-3 py-2 pr-9 transition ${
            saving.includes(n.id) ? "bg-violet/15 text-violet" : firing.includes(n.id) ? "bg-accent/15 text-accent" : "bg-black/20"}`}>
            {confirming === n.id ? (
              <span className="flex items-center justify-between gap-2 text-xs">
                <span className="text-warn">Forget this memory?</span>
                <span className="flex gap-3">
                  <button className="press text-warn hover:underline" onClick={() => { onForget(n.id); setConfirming(null); }}>Forget</button>
                  <button className="press text-ink-2 hover:text-ink" onClick={() => setConfirming(null)}>Keep</button>
                </span>
              </span>
            ) : (
              <>
                {saving.includes(n.id) && <span className="mr-2 rounded bg-violet/20 px-1.5 font-mono text-[0.6rem] uppercase">new</span>}
                {n.text}
                {n.hits > 0 && <span className="ml-2 font-mono text-[0.65rem] text-ink-2">recalled {n.hits}×</span>}
                <button aria-label="Forget this memory" onClick={() => setConfirming(n.id)}
                        className="press absolute right-2 top-2 hidden text-ink-2 hover:text-warn group-hover:block">
                  <Trash2 size={14} />
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
      {memoriesOnly(graph).length > 0 && (
        <div className="sticky -bottom-4 -mx-4 bg-bg-1/95 px-4 py-3 backdrop-blur"> {/* pinned, like Clear all chats */}
          <ConfirmButton label="Clear all memory" onConfirm={onForgetAll}
                         question={`Forget all ${memoriesOnly(graph).length} memories?`} />
        </div>
      )}

      {expanded && (
        <div className="fixed inset-0 z-50 flex flex-col items-center bg-bg-1/95 backdrop-blur">
          <button onClick={() => setExpanded(false)} aria-label="Close"
                  className="press absolute right-6 top-6 rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink">
            <X size={18} />
          </button>
          <p className="eyebrow mt-10 text-xs">
            Core · {state} · {memoriesOnly(graph).length} memories{firing.length > 0 ? ` · recalled ${firing.length}` : ""}
            {saving.length > 0 ? " · storing" : ""}
          </p>
          <div className="w-full flex-1">{core(Math.round(window.innerHeight * 0.66), true)}</div>
          <h2 className="font-display text-6xl font-light tracking-[0.3em] text-ink">MEMORY</h2>
          <p className="mt-2 font-mono text-xs text-ink-2">
            {recall ? `Last recall: "${recall.query}"` : "Strands Harness memory · System 1 decides what to recall"}
          </p>
          <div className="mb-10 mt-4 flex gap-2">
            {STATES.map((s) => (
              <span key={s} className={`rounded-lg border px-3 py-1 font-mono text-xs capitalize ${s === state ? "border-accent/50 bg-accent/10 text-accent" : "border-white/10 text-ink-2"}`}>{s}</span>
            ))}
          </div>
          <div className="absolute bottom-10 left-10">{caption}</div>
          <ul className="absolute bottom-10 right-10 space-y-1.5 font-mono text-[0.7rem] text-ink-2">
            {[["#6EE7B7", "Recalled — fired this turn"], ["#A8F0D9", "Primed — linked to a recalled memory"], ["#CBD5E1", "Outer shell — your knowledge folders, read-only"],
              ["#A78BFA", "Storing — a new memory"], ["#22D3EE", "Resting"]].map(([color, label]) => (
              <li key={label} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} /> {label}
              </li>
            ))}
            <li className="pt-1">Brighter line = used together more often</li>
          </ul>
        </div>
      )}
    </div>
  );
}
