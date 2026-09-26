import { useState } from "react";

export function Composer({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  const send = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };
  return (
    <div className="glass tint flex items-end gap-3 rounded-2xl p-3">
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={1} placeholder="Ask about a trip…"
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                className="flex-1 resize-none bg-transparent text-ink outline-none placeholder:text-ink-2" />
      <button onClick={send} disabled={disabled || !text.trim()}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-bg-1 disabled:opacity-40">
        Send
      </button>
    </div>
  );
}
