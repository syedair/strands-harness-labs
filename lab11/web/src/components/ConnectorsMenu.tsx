import { Plug, Plus, X } from "lucide-react";
import { useState } from "react";
import type { Connector } from "../api";
import { connectorRows, type Switching } from "../connectors";
import { ConnectorSwitch, STATE_LABEL } from "./ConnectorSwitch";

type Props = {
  connectors: Connector[];
  enabled: string[];
  errors: { id: string; error: string }[];
  switching: Switching;
  onToggle: (id: string, on: boolean) => void;
  onAdd: (label: string, command: string, args: string[]) => void;
};

export function ConnectorsMenu({ connectors, enabled, errors, switching, onToggle, onAdd }: Props) {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ label: "", command: "", args: "" });

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} aria-expanded={open}
              className="press flex items-center gap-1.5 rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-xs text-ink-2 hover:border-white/25 hover:text-ink">
        <Plug size={13} className="text-accent" /> Connectors
        {enabled.length > 0 && <span className="rounded-full bg-accent/20 px-1.5 text-accent">{enabled.length}</span>}
      </button>
      {open && (
        <div className="glass animate-rise absolute bottom-full left-0 z-30 mb-2 w-80 space-y-2 rounded-2xl bg-bg-1/95 p-3 shadow-2xl">
          <div className="flex items-center justify-between">
            <p className="eyebrow text-[0.6rem]">MCP connectors</p>
            <button aria-label="Close" onClick={() => setOpen(false)} className="press text-ink-2 hover:text-ink"><X size={14} /></button>
          </div>
          {connectorRows(connectors, { tools: [], connectors: { enabled, errors } }, switching).map((c) => (
            <label key={c.id} className={`flex items-start gap-3 rounded-xl p-2 hover:bg-white/5 ${switching ? "cursor-wait" : "cursor-pointer"}`}>
              <ConnectorSwitch row={c} locked={switching !== null} onToggle={onToggle} />
              <span className="min-w-0 text-sm">
                <span className="block">{c.label}
                  {(c.state === "starting" || c.state === "stopping") && <span className="ml-2 text-xs text-accent">{STATE_LABEL[c.state]}</span>}
                </span>
                <span className="block truncate text-xs text-ink-2">{c.description}</span>
                {c.error && <span className="block text-xs text-warn">Didn't start: {c.error}</span>}
              </span>
            </label>
          ))}
          {adding ? (
            <form className="space-y-2 rounded-xl border border-white/10 p-2"
                  onSubmit={(e) => { e.preventDefault(); onAdd(form.label, form.command, form.args.split(" ").filter(Boolean)); setAdding(false); setForm({ label: "", command: "", args: "" }); }}>
              {(["label", "command", "args"] as const).map((field) => (
                <input key={field} required={field !== "args"} placeholder={field === "args" ? "arguments (space separated)" : field}
                       value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                       className="w-full rounded-lg bg-black/30 px-2 py-1 text-xs text-ink outline-none placeholder:text-ink-2 focus:ring-1 focus:ring-accent/50" />
              ))}
              <button className="press rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-bg-1">Add connector</button>
            </form>
          ) : (
            <button onClick={() => setAdding(true)} className="press flex items-center gap-1.5 px-2 text-xs text-accent-2 hover:underline">
              <Plus size={13} /> Add a custom MCP server
            </button>
          )}
        </div>
      )}
    </div>
  );
}
