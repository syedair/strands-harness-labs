import { Activity, Brain, Database, Plug, Sparkles, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import type { Harness, MemoryGraph } from "../api";
import type { Part } from "../chat";
import { DecisionChip } from "./DecisionChip";

const MemoryGlobe = lazy(() => import("./MemoryGlobe")); // three.js loads only when this tab opens

type Decision = Extract<Part, { kind: "decision" }>;
type Tab = "tools" | "memory" | "skills" | "connectors" | "session" | "system1";
const TABS: [Tab, string, LucideIcon][] = [
  ["tools", "Tools", Wrench], ["memory", "Memory", Brain], ["skills", "Skills", Sparkles],
  ["connectors", "Connectors", Plug], ["session", "Session", Database], ["system1", "System 1", Activity],
];

type Props = { harness: Harness | null; memory: MemoryGraph; fired: string[]; decisions: Decision[] };

function toolSource(tool: string, connectors: string[]): string {
  const connector = connectors.find((c) => tool.startsWith(`${c}_`));
  if (connector) return `MCP · ${connector}`;
  if (tool === "search_memory") return "memory";
  if (tool === "skills") return "skills";
  return "built-in";
}

export function HarnessPanel({ harness, memory, fired, decisions }: Props) {
  const [tab, setTab] = useState<Tab>("memory");
  return (
    <aside className="flex h-full w-[26rem] shrink-0 flex-col border-l border-white/10">
      <p className="eyebrow px-4 pt-4 text-[0.6rem]">Inside the harness</p>
      <nav className="flex flex-wrap gap-1 border-b border-white/10 px-3 py-2">
        {TABS.map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)}
                  className={`press flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs ${tab === id ? "bg-accent/15 text-accent" : "text-ink-2 hover:text-ink"}`}>
            <Icon size={13} /> {label}
          </button>
        ))}
      </nav>
      <div className="flex-1 overflow-y-auto p-4 text-sm">
        {!harness && tab !== "memory" && <p className="text-ink-2">Start a chat to see what's inside.</p>}
        {harness && tab === "tools" && (
          <ul className="space-y-1.5">
            {harness.tools.map((t) => (
              <li key={t} className="animate-rise flex items-center justify-between gap-3 rounded-lg bg-black/20 px-3 py-2">
                <span className="truncate font-mono text-xs">{t}</span>
                <span className="shrink-0 text-[0.65rem] text-ink-2">{toolSource(t, harness.connectors.enabled)}</span>
              </li>
            ))}
          </ul>
        )}
        {tab === "memory" && (
          <Suspense fallback={<p className="text-ink-2">Loading the memory globe…</p>}>
            <MemoryGlobe graph={memory} fired={fired} />
          </Suspense>
        )}
        {harness && tab === "skills" && (
          <ul className="space-y-2">
            {harness.skills.map((s) => (
              <li key={s.name} className="rounded-lg bg-black/20 px-3 py-2">
                <p className="font-mono text-xs text-accent">{s.name}</p>
                <p className="text-ink-2">{s.description}</p>
              </li>
            ))}
          </ul>
        )}
        {harness && tab === "connectors" && (
          harness.connectors.enabled.length === 0 ? (
            <p className="text-ink-2">No connectors on. Turn one on from Connectors under the chat.</p>
          ) : (
            <ul className="space-y-2">
              {harness.connectors.enabled.map((id) => {
                const error = harness.connectors.errors.find((e) => e.id === id);
                const tools = harness.tools.filter((t) => t.startsWith(`${id}_`));
                return (
                  <li key={id} className="rounded-lg bg-black/20 px-3 py-2">
                    <p className={`font-mono text-xs ${error ? "text-warn" : "text-accent"}`}>{id} · {error ? "failed" : `${tools.length} tools`}</p>
                    {error && <p className="text-xs text-warn">{error.error}</p>}
                    {!error && <p className="text-xs text-ink-2">{tools.map((t) => t.slice(id.length + 1)).join(", ")}</p>}
                  </li>
                );
              })}
            </ul>
          )
        )}
        {harness && tab === "session" && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs">
            {[["Chat id", harness.session.id], ["Model", harness.session.model], ["System 1", harness.session.system1_model],
              ["Messages", String(harness.session.messages)],
              ["Files", harness.session.files.map((f) => f.name).join(", ") || "none"]].map(([k, v]) => (
              <div key={k} className="contents"><dt className="eyebrow text-[0.6rem] text-ink-2">{k}</dt><dd className="break-all font-mono">{v}</dd></div>
            ))}
          </dl>
        )}
        {tab === "system1" && (
          decisions.length === 0 ? <p className="text-ink-2">No decisions yet in this chat.</p> : (
            <div className="flex flex-col items-start gap-2">
              {[...decisions].reverse().map((d, i) => <DecisionChip key={i} decision={d} />)}
            </div>
          )
        )}
      </div>
    </aside>
  );
}
