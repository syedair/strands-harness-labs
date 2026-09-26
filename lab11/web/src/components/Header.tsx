import { MessagesSquare, Network, PanelRight, Settings as Gear } from "lucide-react";

export type View = "chat" | "architecture" | "settings";
type Props = { title: string; onTogglePanel: () => void; view: View; onView: (view: View) => void };

const tab = (active: boolean) =>
  `press flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm hover:text-ink ${active ? "border-accent/60 text-ink" : "border-white/15 text-ink-2 hover:border-accent/60"}`;

export function Header({ title, onTogglePanel, view, onView }: Props) {
  return (
    <header className="flex items-end justify-between gap-4 border-b border-white/10 pb-4">
      <div className="min-w-0">
        <p className="eyebrow text-xs">Strands Harness · System 1</p>
        <h1 className="truncate font-display text-2xl font-semibold">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        {view !== "chat" && (
          <button onClick={() => onView("chat")} className={tab(false)}><MessagesSquare size={15} className="text-accent" /> Chat</button>
        )}
        <button onClick={() => onView(view === "architecture" ? "chat" : "architecture")} className={tab(view === "architecture")}>
          <Network size={15} className="text-accent" /> How it works
        </button>
        <button onClick={() => onView(view === "settings" ? "chat" : "settings")} className={tab(view === "settings")}>
          <Gear size={15} className="text-accent" /> Settings
        </button>
        <button onClick={onTogglePanel} aria-label="Inside the harness"
                className="press rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink lg:hidden">
          <PanelRight size={16} />
        </button>
      </div>
    </header>
  );
}
