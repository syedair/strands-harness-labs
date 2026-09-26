// The "How it works" walkthrough: the app's parts, and one turn as a list of steps between them. Pure data.

export type Tone = "plain" | "s1" | "llm" | "save";
export type ArchNode = { id: string; label: string; detail: string; x: number; y: number; tone: Tone; inHarness?: boolean };
export type Step = { from: string; to: string; label: string; title: string; text: string; example?: string; tone: Tone };

export const VIEW = { width: 1110, height: 540 };
export const BOX = { width: 172, height: 62 };
export const HARNESS = { x: 372, y: 44, width: 440, height: 456 }; // the Strands Harness, around its parts

export const NODES: ArchNode[] = [
  { id: "browser", label: "You", detail: "chat in the browser", x: 92, y: 272, tone: "plain" },
  { id: "server", label: "App server", detail: "FastAPI, streams events", x: 276, y: 272, tone: "plain" },
  { id: "session", label: "Session", detail: "chat history on disk", x: 470, y: 122, tone: "plain", inHarness: true },
  { id: "memory", label: "Memory", detail: "markdown notes", x: 470, y: 272, tone: "plain", inHarness: true },
  { id: "skills", label: "Skills", detail: "packing-list, yours…", x: 470, y: 422, tone: "plain", inHarness: true },
  { id: "loop", label: "Agent loop", detail: "gate + check hooks", x: 716, y: 272, tone: "plain", inHarness: true },
  { id: "system1", label: "System 1", detail: "Qwen · Jev · Kev · Laya", x: 1012, y: 106, tone: "s1" },
  { id: "llm", label: "LLM", detail: "Kimi K2.5 on Bedrock", x: 1012, y: 272, tone: "llm" },
  { id: "tools", label: "Tools", detail: "web_fetch · read · MCP", x: 1012, y: 438, tone: "plain" },
];

export const STEPS: Step[] = [
  { from: "browser", to: "server", label: "message", tone: "plain", title: "You send a message",
    text: "The browser posts it to the app server and keeps the connection open to stream the reply back.",
    example: "Pack for 4 days in Istanbul" },
  { from: "server", to: "session", label: "load", tone: "plain", title: "The chat's session loads",
    text: "Every chat is a harness session. The server builds the chat's agent and the harness restores its history from disk." },
  { from: "loop", to: "memory", label: "search", tone: "plain", title: "Memory is searched",
    text: "Before every LLM call the harness searches the saved notes for the message. Its keyword search matches almost anything." },
  { from: "memory", to: "system1", label: "which help?", tone: "s1", title: "System 1 picks the notes that help",
    text: "For each note, System 1 answers one question with a probability. Notes at 0.5 or above are kept, best 5. The memory core fires.",
    example: "Would this fact help answer the message? · The user lives in Dubai → 0.12 · Trip to Istanbul in March → 0.91" },
  { from: "loop", to: "llm", label: "message + notes", tone: "llm", title: "The LLM plans the reply",
    text: "The recalled notes ride along with the message. The LLM decides it needs the weather and asks for a tool." },
  { from: "llm", to: "system1", label: "tool call?", tone: "s1", title: "System 1 gates the tool call",
    text: "The tool gate is a harness intervention: its before_tool_call hook runs before web_fetch does. It asks System 1 two questions, and Python turns the answers into Proceed, Guide (ask instead of guessing), or Deny after 3 tries.",
    example: "Is this a sensible step towards answering? 0.99 · Did the user mention this city? 0.97 → proceed" },
  { from: "loop", to: "tools", label: "run", tone: "plain", title: "The tool runs",
    text: "The harness runs the allowed call. Connectors you turn on add their MCP tools here.",
    example: "wttr.in/Istanbul → Istanbul: ☁️ +22°C" },
  { from: "loop", to: "skills", label: "load", tone: "plain", title: "A skill is loaded",
    text: "Skills are folders of instructions the agent loads when it needs them. This one shapes the packing list." },
  { from: "tools", to: "llm", label: "result", tone: "llm", title: "The LLM writes the answer",
    text: "The forecast and the skill go back to the LLM, with memory recalled again before the call." },
  { from: "llm", to: "system1", label: "complete?", tone: "s1", title: "System 1 checks the answer",
    text: "The completion check is an intervention too, on the after_model_call hook. For multi-part requests it asks whether every part was answered; a half answer gets a Guide and is sent back, up to twice." },
  { from: "server", to: "browser", label: "stream", tone: "plain", title: "The answer streams to you",
    text: "Text arrives as it's written. Every step above becomes an event, folded into one row above the answer." },
  { from: "loop", to: "memory", label: "save", tone: "save", title: "What it learned is saved",
    text: "After the reply, the harness pulls new facts out of the conversation and saves them as dated notes. They gather in violet.",
    example: "User is planning a 4-day trip to Istanbul" },
];

export type Scene = { shown: Set<string>; current: Step | null; past: Step[] };

/** What's on screen at step `i` (-1 = before the first step): parts used so far, this step, and the ones before. */
export function sceneAt(i: number): Scene {
  const at = Math.min(Math.max(i, -1), STEPS.length - 1);
  const done = STEPS.slice(0, at + 1);
  const shown = new Set(["browser", ...done.flatMap((s) => [s.from, s.to])]);
  return { shown, current: at >= 0 ? STEPS[at] : null, past: done.slice(0, -1) };
}

/** Where a link between two boxes starts and ends: on their edges, not their centres. */
export function linkEnds(a: ArchNode, b: ArchNode, gap = 6) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const reach = Math.min((BOX.width / 2 + gap) / Math.abs(dx || 1e-9), (BOX.height / 2 + gap) / Math.abs(dy || 1e-9));
  return { x1: a.x + dx * reach, y1: a.y + dy * reach, x2: b.x - dx * reach, y2: b.y - dy * reach };
}
