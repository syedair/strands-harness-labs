import { PanelRight } from "lucide-react";

export function Header({ title, onTogglePanel }: { title: string; onTogglePanel: () => void }) {
  return (
    <header className="flex items-end justify-between gap-4 border-b border-white/10 pb-4">
      <div className="min-w-0">
        <p className="eyebrow text-xs">Strands Harness · System 1</p>
        <h1 className="truncate font-display text-2xl font-semibold">{title}</h1>
      </div>
      <button onClick={onTogglePanel} aria-label="Inside the harness"
              className="press rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink lg:hidden">
        <PanelRight size={16} />
      </button>
    </header>
  );
}
