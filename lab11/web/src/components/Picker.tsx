import { ChevronDown } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Choice } from "../api";

type Props = { label: string; icon: LucideIcon; choices: Choice[]; value: string; onChange: (id: string) => void };

/** A themed select. Choices that can't run are disabled, with their fix as a tooltip. */
export function Picker({ label, icon: Icon, choices, value, onChange }: Props) {
  return (
    <label className="press relative flex items-center gap-1.5 rounded-full border border-white/10 bg-black/20 py-1 pl-2.5 pr-7 text-xs text-ink-2 hover:border-white/25 hover:text-ink"
           title={label}>
      <Icon size={13} className="text-accent" />
      <span className="sr-only">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}
              className="appearance-none bg-transparent text-ink outline-none">
        {choices.map((c) => (
          <option key={c.id} value={c.id} disabled={!c.available} title={c.reason ?? ""} className="bg-bg-1">
            {c.label}{c.available ? "" : " — unavailable"}
          </option>
        ))}
      </select>
      <ChevronDown size={13} className="pointer-events-none absolute right-2" />
    </label>
  );
}
