import type { Part } from "../chat";

type Decision = Extract<Part, { kind: "decision" }>;

export function DecisionChip({ decision }: { decision: Decision }) {
  const blocked = decision.action !== "proceed";
  const [icon, text] =
    decision.source === "gate"
      ? ["🛡", blocked ? `Gate blocked: ${decision.why ?? "guessed argument"}` : "Gate allowed the call"]
      : [blocked ? "↻" : "✓", blocked ? "Sent back to finish" : "Completion check passed"];
  const tone = blocked ? "border-warn/50 text-warn" : "border-accent/40 text-accent";
  return (
    <div className={`glass inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs ${tone}`} title={JSON.stringify(decision.probs)}>
      <span>{icon}</span>
      <span className="text-ink">{text}</span>
      {decision.p !== null && <span className="font-mono">P = {decision.p.toFixed(2)}</span>}
    </div>
  );
}
