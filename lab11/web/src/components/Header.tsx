import { ChevronDown, Cpu, SquarePen } from "lucide-react";
import type { System1Option } from "../api";

type Props = { options: System1Option[]; value: string; onChange: (id: string) => void; onNewChat: () => void };

export function Header({ options, value, onChange, onNewChat }: Props) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-4">
      <div>
        <p className="eyebrow text-xs">Strands Harness · System 1</p>
        <h1 className="font-display text-2xl font-semibold">Travel assistant</h1>
      </div>
      <div className="flex items-center gap-3">
        <label className="eyebrow flex items-center gap-1.5 text-[0.65rem] text-ink-2" htmlFor="system1">
          <Cpu size={14} /> System 1
        </label>
        <div className="relative">
          <select id="system1" value={value} onChange={(e) => onChange(e.target.value)}
                  className="glass press appearance-none rounded-full bg-transparent py-2 pl-4 pr-9 text-sm text-ink outline-none">
            {options.map((o) => (
              <option key={o.id} value={o.id} disabled={!o.available} title={o.reason ?? ""} className="bg-bg-1">
                {o.label}{o.available ? "" : " — unavailable"}
              </option>
            ))}
          </select>
          <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-2" />
        </div>
        <button onClick={onNewChat}
                className="press flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2 text-sm text-ink-2 hover:border-white/30 hover:text-ink">
          <SquarePen size={15} /> New chat
        </button>
      </div>
    </header>
  );
}
