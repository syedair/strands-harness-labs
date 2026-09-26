import { MessageSquare, SquarePen, Trash2 } from "lucide-react";
import { useState } from "react";
import type { ChatSummary } from "../api";

type Props = {
  chats: ChatSummary[];
  activeId: string | null;
  onOpen: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
};

const DAY = 24 * 60 * 60 * 1000;

export function Sidebar({ chats, activeId, onOpen, onNew, onDelete }: Props) {
  const [confirming, setConfirming] = useState<string | null>(null);
  const today = chats.filter((c) => Date.now() - c.updated_at < DAY);
  const earlier = chats.filter((c) => Date.now() - c.updated_at >= DAY);

  const group = (title: string, items: ChatSummary[]) =>
    items.length > 0 && (
      <div className="space-y-1">
        <p className="eyebrow px-2 text-[0.6rem] text-ink-2">{title}</p>
        {items.map((chat) => (
          <div key={chat.id} className={`group relative rounded-xl ${chat.id === activeId ? "bg-white/10" : "hover:bg-white/5"}`}>
            {confirming === chat.id ? (
              <div className="flex items-center justify-between gap-2 px-3 py-2 text-xs">
                <span className="text-warn">Delete this chat?</span>
                <span className="flex gap-2">
                  <button className="press text-warn hover:underline" onClick={() => { onDelete(chat.id); setConfirming(null); }}>Delete</button>
                  <button className="press text-ink-2 hover:text-ink" onClick={() => setConfirming(null)}>Keep</button>
                </span>
              </div>
            ) : (
              <>
                <button onClick={() => onOpen(chat.id)} className="press flex w-full items-center gap-2 px-3 py-2 text-left text-sm">
                  <MessageSquare size={14} className="shrink-0 text-ink-2" />
                  <span className="truncate pr-6">{chat.title}</span>
                </button>
                <button aria-label="Delete chat" onClick={() => setConfirming(chat.id)}
                        className="press absolute right-2 top-1/2 hidden -translate-y-1/2 text-ink-2 hover:text-warn group-hover:block">
                  <Trash2 size={14} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    );

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col gap-4 border-r border-white/10 p-3">
      <button onClick={onNew}
              className="glass press flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm hover:border-accent/60">
        <SquarePen size={15} className="text-accent" /> New chat
      </button>
      <nav className="flex-1 space-y-4 overflow-y-auto">
        {group("Today", today)}
        {group("Earlier", earlier)}
        {chats.length === 0 && <p className="px-2 text-sm text-ink-2">Your chats will appear here.</p>}
      </nav>
    </aside>
  );
}
