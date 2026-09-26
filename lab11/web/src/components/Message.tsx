import { Brain, BrainCircuit, ChevronRight, RotateCcw, ShieldAlert, ShieldCheck, TriangleAlert, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import Markdown from "react-markdown";
import type { AssistantTurn, Part, Turn } from "../chat";
import { splitTurn } from "../chat";
import { DecisionChip } from "./DecisionChip";
import { ToolCard } from "./ToolCard";
import { Waiting } from "./Waiting";

function Step({ part }: { part: Part }) {
  if (part.kind === "tool") return <ToolCard name={part.name} input={part.input} />;
  if (part.kind === "decision") return <DecisionChip decision={part} />;
  if (part.kind === "memory") {
    const detail = part.ids.map((id, n) => `${id.replace(/\.md$/, "")}  ${part.scores[n]?.toFixed(2) ?? ""}`).join("\n");
    return (
      <div title={`Searched for: "${part.query}"\n${detail}`}
           className="animate-rise inline-flex items-center gap-2 rounded-full border border-accent-2/40 px-3 py-1 text-xs text-accent-2">
        <Brain size={14} />
        <span className="text-ink">Recalled {part.ids.length} {part.ids.length === 1 ? "memory" : "memories"}</span>
        {part.scores.length > 0 && <span className="font-mono">best {Math.max(...part.scores).toFixed(2)}</span>}
      </div>
    );
  }
  if (part.kind === "stored") {
    return (
      <div className="animate-rise inline-flex items-center gap-2 rounded-full border border-violet/50 px-3 py-1 text-xs text-violet">
        <BrainCircuit size={14} />
        <span className="text-ink">Saved {part.ids.length === 1 ? "a new memory" : `${part.ids.length} new memories`}</span>
      </div>
    );
  }
  // text that isn't the final answer: a preamble ("I'll check…") or a draft the check sent back
  return <p className={`text-sm text-ink-2 ${part.discarded ? "line-through opacity-60" : ""}`}>{part.text}</p>;
}

function Steps({ turn }: { turn: AssistantTurn }) {
  const { steps, summary } = splitTurn(turn);
  const [choice, setChoice] = useState<boolean | null>(null);
  if (steps.length === 0) return null;
  const open = choice ?? turn.streaming; // live while working, collapsed once the answer is in
  const facts: [LucideIcon, string, string][] = [];
  if (summary.recalled) facts.push([Brain, `recalled ${summary.recalled}`, "text-accent-2"]);
  if (summary.tools) facts.push([Wrench, `${summary.tools} ${summary.tools === 1 ? "tool" : "tools"}`, "text-accent-2"]);
  if (summary.blocked) facts.push([ShieldAlert, `gate blocked ${summary.blocked}`, "text-warn"]);
  if (summary.allowed) facts.push([ShieldCheck, `gate allowed ${summary.allowed}`, "text-accent"]);
  if (summary.sentBack) facts.push([RotateCcw, `${summary.sentBack} ${summary.sentBack === 1 ? "draft" : "drafts"} sent back`, "text-warn"]);
  if (summary.saved) facts.push([BrainCircuit, `saved ${summary.saved}`, "text-violet"]);
  return (
    <div className="rounded-xl border border-white/10 bg-black/20">
      <button onClick={() => setChoice(!open)} aria-expanded={open}
              className="press flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-left text-xs text-ink-2 hover:text-ink">
        <ChevronRight size={14} className={`transition ${open ? "rotate-90" : ""}`} />
        <span className="eyebrow text-[0.6rem]">{turn.streaming ? "Working" : "Steps"}</span>
        {facts.map(([Icon, label, tone]) => (
          <span key={label} className={`flex items-center gap-1 ${tone}`}><Icon size={13} /> {label}</span>
        ))}
      </button>
      {open && (
        <div className="flex flex-col items-start gap-2 border-t border-white/10 px-3 py-3">
          {steps.map((part, i) => <Step key={i} part={part} />)}
        </div>
      )}
    </div>
  );
}

export function Message({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="animate-rise max-w-[75%] rounded-2xl rounded-br-md bg-white/10 px-4 py-2 text-ink">{turn.text}</div>
      </div>
    );
  }
  const { answer } = splitTurn(turn);
  return (
    <div className="glass animate-rise max-w-[85%] space-y-3 rounded-2xl rounded-bl-md px-4 py-3">
      <Steps turn={turn} />
      {answer && (
        <div className="reply leading-relaxed">
          <Markdown>{answer.text}</Markdown>
        </div>
      )}
      <Waiting turn={turn} />
      {turn.error && (
        <p className="flex items-center gap-2 text-sm text-warn"><TriangleAlert size={16} /> {turn.error}</p>
      )}
    </div>
  );
}
