import { LoaderCircle, Upload } from "lucide-react";
import { useRef, useState } from "react";
import type { Harness } from "../api";

/** The skills the harness found, and a button to add one (a SKILL.md, or the skill folder as a .zip). */
export function SkillsTab({ skills, onAdd }: { skills: Harness["skills"]; onAdd: (file: File) => Promise<void> }) {
  const input = useRef<HTMLInputElement>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add(file: File) {
    setAdding(true);
    setError(null);
    try {
      await onAdd(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {skills.map((s) => (
          <li key={s.name} className="animate-rise rounded-lg bg-black/20 px-3 py-2">
            <p className="font-mono text-xs text-accent">{s.name}</p>
            <p className="text-ink-2">{s.description}</p>
          </li>
        ))}
      </ul>
      <button onClick={() => input.current?.click()} disabled={adding}
              className="glass press flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm hover:border-accent/60 disabled:cursor-wait disabled:opacity-60">
        {adding ? <LoaderCircle size={15} className="animate-spin text-accent" /> : <Upload size={15} className="text-accent" />}
        {adding ? "Adding skill…" : "Add skill"}
      </button>
      <input ref={input} type="file" accept=".md,.zip" hidden
             onChange={(e) => { const f = e.target.files?.[0]; if (f) add(f); e.target.value = ""; }} />
      {error && <p className="text-xs text-warn">{error}</p>}
      <p className="text-xs text-ink-2">
        Upload a SKILL.md, or the skill folder as a .zip (with its references and scripts). Chats use it from their next
        message. This agent has no shell, so a skill's scripts won't run; it can read the rest.
      </p>
    </div>
  );
}
