import { Trash2 } from "lucide-react";
import { useState } from "react";

/** A destructive action with an inline second step instead of a browser dialog. */
export function ConfirmButton({ label, question, disabled, onConfirm }: {
  label: string; question: string; disabled?: boolean; onConfirm: () => Promise<void> | void;
}) {
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const confirm = async () => {
    setAsking(false);
    setError(null);
    try {
      await onConfirm();
    } catch (e) {
      setError(`Couldn't delete: ${e instanceof Error ? e.message : String(e)}`); // e.g. the server is older than this button
    }
  };
  if (error) {
    return (
      <button onClick={() => setError(null)} className="press w-full rounded-xl border border-warn/40 px-3 py-2 text-left text-xs text-warn">
        {error} <span className="text-ink-2">· dismiss</span>
      </button>
    );
  }
  return asking ? (
    <div className="flex items-center justify-between gap-2 rounded-xl border border-warn/40 px-3 py-2 text-xs">
      <span className="text-warn">{question}</span>
      <span className="flex gap-3">
        <button className="press font-semibold text-warn hover:underline" onClick={confirm}>Delete</button>
        <button className="press text-ink-2 hover:text-ink" onClick={() => setAsking(false)}>Keep</button>
      </span>
    </div>
  ) : (
    <button disabled={disabled} onClick={() => setAsking(true)}
            className="press flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs text-ink-2 hover:border-warn/50 hover:text-warn disabled:cursor-not-allowed disabled:opacity-40">
      <Trash2 size={13} /> {label}
    </button>
  );
}
