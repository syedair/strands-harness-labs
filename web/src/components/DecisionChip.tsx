import type { Part } from "../chat";

type Decision = Extract<Part, { kind: "decision" }>;

export function DecisionChip({ decision }: { decision: Decision }) {
  const blocked = decision.action !== "proceed";
  const [icon, text, p] =
    decision.source === "gate"
      ? ["🛡", blocked ? "Gate blocked a guessed argument" : "Gate allowed the call", decision.probs.args_grounded]
      : [blocked ? "↻" : "✓", blocked ? "Sent back to finish" : "Completion check passed", decision.probs.answered_everything];
  const tone = blocked ? "border-warn/50 text-warn" : "border-accent/40 text-accent";
  return (
    <div className={`glass inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs ${tone}`} title={JSON.stringify(decision.probs)}>
      <span>{icon}</span>
      <span className="text-ink">{text}</span>
      <span className="font-mono">P = {p?.toFixed(2)}</span>
    </div>
  );
}
