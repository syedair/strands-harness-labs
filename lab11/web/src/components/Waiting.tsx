import { LoaderCircle } from "lucide-react";
import type { AssistantTurn } from "../chat";
import { statusOf } from "../chat";

/** Shows what the assistant is doing while a reply is in progress. */
export function Waiting({ turn }: { turn: AssistantTurn }) {
  const status = statusOf(turn);
  if (status === "thinking") {
    return (
      <div className="flex items-center gap-2 text-sm text-ink-2" aria-live="polite">
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </span>
        Thinking
      </div>
    );
  }
  if (status === "working") {
    const tool = [...turn.parts].reverse().find((p) => p.kind === "tool");
    return (
      <div className="flex items-center gap-2 text-sm text-ink-2" aria-live="polite">
        <LoaderCircle size={16} className="animate-spin text-accent" />
        Running {tool?.kind === "tool" ? tool.name : "a tool"}…
      </div>
    );
  }
  if (status === "writing") return <span className="inline-block h-4 w-1.5 animate-pulse rounded-sm bg-accent align-middle" />;
  return null;
}
