import { Brain, BrainCircuit, TriangleAlert } from "lucide-react";
import Markdown from "react-markdown";
import type { Turn } from "../chat";
import { DecisionChip } from "./DecisionChip";
import { ToolCard } from "./ToolCard";
import { Waiting } from "./Waiting";

export function Message({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="animate-rise max-w-[75%] rounded-2xl rounded-br-md bg-white/10 px-4 py-2 text-ink">{turn.text}</div>
      </div>
    );
  }
  return (
    <div className="glass animate-rise max-w-[85%] space-y-3 rounded-2xl rounded-bl-md px-4 py-3">
      {turn.parts.map((part, i) => {
        if (part.kind === "tool") return <ToolCard key={i} name={part.name} input={part.input} />;
        if (part.kind === "decision") return <DecisionChip key={i} decision={part} />;
        if (part.kind === "memory") {
          const detail = part.ids.map((id, n) => `${id.replace(/\.md$/, "")}  ${part.scores[n]?.toFixed(2) ?? ""}`).join("\n");
          return (
            <div key={i} title={`Searched for: "${part.query}"\n${detail}`}
                 className="animate-rise inline-flex items-center gap-2 rounded-full border border-accent-2/40 px-3 py-1 text-xs text-accent-2">
              <Brain size={14} />
              <span className="text-ink">Recalled {part.ids.length} {part.ids.length === 1 ? "memory" : "memories"}</span>
              {part.scores.length > 0 && <span className="font-mono">best {Math.max(...part.scores).toFixed(2)}</span>}
            </div>
          );
        }
        if (part.kind === "stored") {
          return (
            <div key={i} className="animate-rise inline-flex items-center gap-2 rounded-full border border-violet/50 px-3 py-1 text-xs text-violet">
              <BrainCircuit size={14} />
              <span className="text-ink">Saved {part.ids.length === 1 ? "a new memory" : `${part.ids.length} new memories`}</span>
            </div>
          );
        }
        if (part.discarded) {
          return <p key={i} className="text-ink-2 line-through opacity-50">{part.text}</p>;
        }
        return (
          <div key={i} className="reply leading-relaxed">
            <Markdown>{part.text}</Markdown>
          </div>
        );
      })}
      <Waiting turn={turn} />
      {turn.error && (
        <p className="flex items-center gap-2 text-sm text-warn"><TriangleAlert size={16} /> {turn.error}</p>
      )}
    </div>
  );
}
