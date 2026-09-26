import { LoaderCircle } from "lucide-react";
import type { ConnectorRow } from "../connectors";

/** A connector's checkbox: shows where it's going at once, greyed out with a spinner while the harness applies it. */
export function ConnectorSwitch({ row, locked, onToggle }: { row: ConnectorRow; locked: boolean; onToggle: (id: string, on: boolean) => void }) {
  const changing = row.state === "starting" || row.state === "stopping";
  const checked = row.state !== "off" && row.state !== "stopping";
  return changing ? (
    <LoaderCircle size={15} aria-label={row.state} className="mt-0.5 shrink-0 animate-spin text-accent" />
  ) : (
    <input type="checkbox" checked={checked} disabled={locked} aria-label={`Turn ${row.label} on or off`}
           onChange={(e) => onToggle(row.id, e.target.checked)}
           className="mt-1 shrink-0 accent-[#6EE7B7] disabled:cursor-not-allowed disabled:opacity-40" />
  );
}

export const STATE_LABEL: Record<ConnectorRow["state"], string> = {
  on: "on", off: "off", failed: "failed", starting: "starting…", stopping: "stopping…",
};
