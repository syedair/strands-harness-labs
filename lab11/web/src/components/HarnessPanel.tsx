import { Activity, Brain, Database, Plug, Sparkles, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import type { Connector, Harness, MemoryGraph } from "../api";
import type { Part } from "../chat";
import { DecisionChip } from "./DecisionChip";
import { SkillsTab } from "./SkillsTab";
import type { CoreState } from "./MemoryCore";
import type { Recall } from "./MemoryGlobe";
import type { Burst, Ghosts } from "../globe";
import { connectorRows, type Switching } from "../connectors";
import { ConnectorSwitch, STATE_LABEL } from "./ConnectorSwitch";

const MemoryGlobe = lazy(() => import("./MemoryGlobe")); // three.js loads only when this tab opens

type Decision = Extract<Part, { kind: "decision" }>;
type Tab = "tools" | "memory" | "skills" | "connectors" | "session" | "system1";
const TABS: [Tab, string, LucideIcon][] = [
  ["tools", "Tools", Wrench], ["memory", "Memory", Brain], ["skills", "Skills", Sparkles],
  ["connectors", "Connectors", Plug], ["session", "Session", Database], ["system1", "System 1", Activity],
];

type Props = {
  harness: Harness | null; memory: MemoryGraph; fired: Burst; stored: Burst; forgot: Ghosts; recall: Recall | null;
  connectors: Connector[]; switching: Switching; onAddSkill: (file: File) => Promise<void>; onToggleConnector: (id: string, on: boolean) => void;
  decisions: Decision[]; state: CoreState; onForget: (id: string) => void;
};

function toolSource(tool: string, connectors: string[]): string {
  const connector = connectors.find((c) => tool.startsWith(`${c}_`));
  if (connector) return `MCP · ${connector}`;
  if (tool === "search_memory") return "memory";
  if (tool === "skills") return "skills";
  return "built-in";
}

export function HarnessPanel({ harness, connectors, switching, onAddSkill, onToggleConnector, memory, fired, stored, forgot, recall, decisions, state, onForget }: Props) {
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
            <MemoryGlobe graph={memory} fired={fired} stored={stored} forgot={forgot} recall={recall} state={state} onForget={onForget} />
          </Suspense>
        )}
        {harness && tab === "skills" && <SkillsTab skills={harness.skills} onAdd={onAddSkill} />}
        {harness && tab === "connectors" && (
          <ul className="space-y-2">
            {connectorRows(connectors, harness, switching).map((c) => (
              <li key={c.id} className={`flex items-start gap-3 rounded-lg bg-black/20 px-3 py-2 ${switching && switching.id !== c.id ? "opacity-60" : ""}`}>
                <ConnectorSwitch row={c} locked={switching !== null} onToggle={onToggleConnector} />
                <div className="min-w-0">
                  <p className="text-sm">{c.label}{" "}
                    <span className={`font-mono text-[0.65rem] ${c.state === "failed" ? "text-warn" : c.state === "on" ? "text-accent" : "text-ink-2"}`}>
                      {c.state === "on" ? `on · ${c.tools.length} tools` : STATE_LABEL[c.state]}
                    </span>
                  </p>
                  {c.error && <p className="text-xs text-warn">{c.error}</p>}
                  {c.state === "on" && <p className="text-xs text-ink-2">{c.tools.join(", ")}</p>}
                  {c.state === "off" && c.description && <p className="text-xs text-ink-2">{c.description}</p>}
                </div>
              </li>
            ))}
          </ul>
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
