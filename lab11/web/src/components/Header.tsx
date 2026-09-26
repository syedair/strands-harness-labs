import { MessagesSquare, Network, PanelRight } from "lucide-react";

type Props = { title: string; onTogglePanel: () => void; showingArchitecture: boolean; onToggleArchitecture: () => void };

export function Header({ title, onTogglePanel, showingArchitecture, onToggleArchitecture }: Props) {
  return (
    <header className="flex items-end justify-between gap-4 border-b border-white/10 pb-4">
      <div className="min-w-0">
        <p className="eyebrow text-xs">Strands Harness · System 1</p>
        <h1 className="truncate font-display text-2xl font-semibold">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
      <button onClick={onToggleArchitecture}
              className="press flex items-center gap-2 rounded-full border border-white/15 px-3 py-1.5 text-sm text-ink-2 hover:border-accent/60 hover:text-ink">
        {showingArchitecture ? <><MessagesSquare size={15} className="text-accent" /> Chat</> : <><Network size={15} className="text-accent" /> How it works</>}
      </button>
      <button onClick={onTogglePanel} aria-label="Inside the harness"
              className="press rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink lg:hidden">
        <PanelRight size={16} />
      </button>
      </div>
    </header>
  );
}
