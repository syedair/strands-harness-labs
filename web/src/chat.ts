// Folds the event stream into one assistant turn. Pure, so it's easy to test.
import type { ChatEvent } from "./api";

export type Part =
  | { kind: "text"; text: string; discarded: boolean }
  | { kind: "tool"; name: string; input: Record<string, unknown> }
  | ({ kind: "decision" } & Omit<Extract<ChatEvent, { type: "decision" }>, "type">);

export type AssistantTurn = { role: "assistant"; parts: Part[]; streaming: boolean; error?: string };
export type UserTurn = { role: "user"; text: string };
export type Turn = UserTurn | AssistantTurn;

export const newAssistantTurn = (): AssistantTurn => ({ role: "assistant", parts: [], streaming: true });

export function applyEvent(turn: AssistantTurn, event: ChatEvent): AssistantTurn {
  const parts = [...turn.parts];
  const last = parts[parts.length - 1];
  switch (event.type) {
    case "text":
      if (last?.kind === "text" && !last.discarded) parts[parts.length - 1] = { ...last, text: last.text + event.delta };
      else parts.push({ kind: "text", text: event.delta, discarded: false });
      return { ...turn, parts };
    case "tool":
      return { ...turn, parts: [...parts, { kind: "tool", name: event.name, input: event.input }] };
    case "decision":
      if (event.source === "check" && event.action !== "proceed") {
        // the model's draft was thrown away and it's trying again
        const i = parts.findLastIndex((p) => p.kind === "text" && !p.discarded);
        if (i >= 0) parts[i] = { ...(parts[i] as Extract<Part, { kind: "text" }>), discarded: true };
      }
      return { ...turn, parts: [...parts, { kind: "decision", source: event.source, action: event.action,
                                             why: event.why, p: event.p, probs: event.probs }] };
    case "done":
      return { ...turn, streaming: false };
    case "error":
      return { ...turn, streaming: false, error: event.message };
  }
}

export type Status = "thinking" | "working" | "writing" | "done";

/** What the assistant is doing right now, for the waiting indicators. */
export function statusOf(turn: AssistantTurn): Status {
  if (!turn.streaming) return "done";
  const last = turn.parts[turn.parts.length - 1];
  if (!last) return "thinking";
  if (last.kind === "tool") return "working"; // the tool is running
  if (last.kind === "decision" && last.source === "gate" && last.action === "proceed") return "working";
  if (last.kind === "text" && !last.discarded) return "writing";
  return "thinking";
}
