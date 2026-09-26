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
        <label className="eyebrow text-[0.65rem] text-ink-2" htmlFor="system1">System 1</label>
        <select id="system1" value={value} onChange={(e) => onChange(e.target.value)}
                className="glass rounded-full bg-transparent px-4 py-2 text-sm text-ink outline-none focus:border-accent">
          {options.map((o) => (
            <option key={o.id} value={o.id} disabled={!o.available} title={o.reason ?? ""} className="bg-bg-1">
              {o.label}{o.available ? "" : " — unavailable"}
            </option>
          ))}
        </select>
        <button onClick={onNewChat} className="rounded-full border border-white/15 px-4 py-2 text-sm text-ink-2 hover:text-ink">
          New chat
        </button>
      </div>
    </header>
  );
}
