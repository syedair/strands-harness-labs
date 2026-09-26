import { LoaderCircle, SendHorizontal } from "lucide-react";
import { useState } from "react";

export function Composer({ busy, disabled, onSend }: { busy: boolean; disabled: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  const blocked = busy || disabled;
  const send = () => {
    if (!text.trim() || blocked) return;
    onSend(text.trim());
    setText("");
  };
  return (
    <div className="glass tint flex items-end gap-3 rounded-2xl p-3 transition focus-within:shadow-[0_0_0_4px_rgba(110,231,183,0.15)]">
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={1} placeholder="Ask about a trip…"
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                className="flex-1 resize-none bg-transparent py-2 text-ink outline-none placeholder:text-ink-2" />
      <button onClick={send} disabled={blocked || !text.trim()} aria-label="Send"
              className="press flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-bg-1 hover:brightness-110 disabled:opacity-40">
        {busy ? <LoaderCircle size={18} className="animate-spin" /> : <SendHorizontal size={18} />}
      </button>
    </div>
  );
}
