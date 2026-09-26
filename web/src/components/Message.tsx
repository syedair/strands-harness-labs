import Markdown from "react-markdown";
import type { Turn } from "../chat";
import { DecisionChip } from "./DecisionChip";
import { ToolCard } from "./ToolCard";

export function Message({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-md bg-white/10 px-4 py-2 text-ink">{turn.text}</div>
      </div>
    );
  }
  return (
    <div className="glass max-w-[85%] space-y-3 rounded-2xl rounded-bl-md px-4 py-3">
      {turn.parts.map((part, i) => {
        if (part.kind === "tool") return <ToolCard key={i} name={part.name} input={part.input} />;
        if (part.kind === "decision") return <DecisionChip key={i} decision={part} />;
        if (part.discarded) {
          return <p key={i} className="text-ink-2 line-through opacity-50">{part.text}</p>;
        }
        return (
          <div key={i} className="reply leading-relaxed">
            <Markdown>{part.text}</Markdown>
          </div>
        );
      })}
      {turn.streaming && <span className="inline-block h-4 w-2 animate-pulse bg-accent align-middle" />}
      {turn.error && <p className="text-sm text-warn">⚠ {turn.error}</p>}
    </div>
  );
}
