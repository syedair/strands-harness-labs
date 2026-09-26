// The "How it works" walkthrough: the app's parts, and one turn as a list of steps between them. Pure data.

export type Tone = "plain" | "s1" | "llm" | "save";
export type ArchNode = { id: string; label: string; detail: string; x: number; y: number; tone: Tone; inHarness?: boolean };
export type Step = { from: string; to: string; back?: boolean; label: string; title: string; text: string; example?: string; tone: Tone };

export const VIEW = { width: 1400, height: 530 };
export const BOX = { width: 164, height: 62 };
export const HARNESS = { x: 452, y: 40, width: 556, height: 466 }; // the Strands Harness, around its parts

export const NODES: ArchNode[] = [
  { id: "browser", label: "You", detail: "chat in the browser", x: 96, y: 170, tone: "plain" },
  { id: "server", label: "App server", detail: "FastAPI, streams events", x: 330, y: 170, tone: "plain" },
  { id: "agent", label: "Agent", detail: "orchestrates every step", x: 730, y: 170, tone: "plain", inHarness: true },
  { id: "session", label: "Session", detail: "chat history on disk", x: 548, y: 420, tone: "plain", inHarness: true },
  { id: "memory", label: "Memory", detail: "markdown notes", x: 730, y: 420, tone: "plain", inHarness: true },
  { id: "skills", label: "Skills", detail: "packing-list, yours…", x: 912, y: 420, tone: "plain", inHarness: true },
  { id: "system1", label: "System 1", detail: "Qwen · Jev · Kev · Laya", x: 1236, y: 80, tone: "s1" },
  { id: "llm", label: "LLM", detail: "Kimi K2.5 on Bedrock", x: 1236, y: 250, tone: "llm" },
  { id: "tools", label: "Tools", detail: "web_fetch · read · MCP", x: 1236, y: 420, tone: "plain" },
];

export const STEPS: Step[] = [
  { from: "browser", to: "server", label: "message", tone: "plain", title: "You send a message",
    text: "The browser posts it to the app server and keeps the connection open for the reply.",
    example: "Pack for 4 days in Istanbul" },
  { from: "server", to: "agent", label: "message", tone: "plain", title: "The server hands it to the Agent",
    text: "Every chat has its own Agent. From here on, the Agent orchestrates every step: it calls each part and decides what happens next." },
  { from: "agent", to: "session", back: true, label: "history", tone: "plain", title: "The Agent restores the chat",
    text: "Every chat is a harness session, so the Agent picks up the conversation from disk where it left off." },
  { from: "agent", to: "memory", back: true, label: "search", tone: "plain", title: "The Agent searches memory",
    text: "Before every LLM call the Agent searches the saved notes. The keyword search matches almost anything, so the hits need checking." },
  { from: "agent", to: "system1", back: true, label: "which notes help?", tone: "s1", title: "System 1 picks the notes that help",
    text: "For each note, System 1 answers one question with a probability. Notes at 0.5 or above are kept, best 5. The memory core fires.",
    example: "Would this fact help answer the message? · Trip to Istanbul in March → 0.91 · Favourite airline → 0.08" },
  { from: "agent", to: "llm", back: true, label: "message + notes", tone: "llm", title: "The LLM asks for a skill",
    text: "The recalled notes ride along with the message. The LLM sees a packing-list skill is available and asks to load it." },
  { from: "agent", to: "skills", back: true, label: "packing-list", tone: "plain", title: "The Agent loads the skill",
    text: "Skills are folders of instructions. This one says to check the forecast before listing what to pack." },
  { from: "agent", to: "llm", back: true, label: "skill", tone: "llm", title: "The LLM asks for the forecast",
    text: "Following the skill, the LLM asks the Agent to run web_fetch for Istanbul's weather.",
    example: "web_fetch https://wttr.in/Istanbul?format=3" },
  { from: "agent", to: "system1", back: true, label: "allow the tool?", tone: "s1", title: "System 1 gates the tool call",
    text: "The tool gate is a harness intervention: its before_tool_call hook runs before the tool does. It asks System 1 two questions, and Python turns the answers into Proceed, Guide (ask instead of guessing), or Deny after 3 tries.",
    example: "Is this a sensible step towards answering? 0.99 · Did the user mention this city? 0.97 → Proceed" },
  { from: "agent", to: "tools", back: true, label: "web_fetch", tone: "plain", title: "The tool runs",
    text: "The Agent runs the allowed call. Connectors you turn on add their MCP tools here.",
    example: "Istanbul: ☁️ +22°C" },
  { from: "agent", to: "llm", back: true, label: "forecast", tone: "llm", title: "The LLM writes the answer",
    text: "The forecast goes back to the LLM, which writes the packing list. Memory is searched and checked again before this call." },
  { from: "agent", to: "system1", back: true, label: "complete?", tone: "s1", title: "System 1 checks the answer",
    text: "The completion check is an intervention too, on the after_model_call hook. For multi-part requests it asks whether every part was answered; a half answer is sent back, up to twice." },
  { from: "agent", to: "server", label: "answer", tone: "plain", title: "The Agent returns the answer",
    text: "Every step so far was also reported as an event: recalls, tool calls, gate and check decisions." },
  { from: "server", to: "browser", back: true, label: "stream", tone: "plain", title: "The answer streams to you",
    text: "Text arrives as it's written, with the steps folded into one row above it. The connection stays open for one last step." },
  { from: "server", to: "agent", label: "save", tone: "save", title: "The server asks the Agent to remember",
    text: "Once the reply is out, the server asks the Agent to save what it learned." },
  { from: "agent", to: "memory", back: true, label: "new notes", tone: "save", title: "What it learned is saved",
    text: "The Agent pulls new facts out of the conversation and saves them as dated notes. They gather in violet on the memory core.",
    example: "User is planning a 4-day trip to Istanbul" },
];

/** Where a step leaves the flow: a round trip comes back to where it started. */
export const endOf = (step: Step) => (step.back ? step.from : step.to);

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

/** Where a link's label sits: beside the middle of the line, pushed far enough that its box never touches it. */
export function labelSpot(ends: { x1: number; y1: number; x2: number; y2: number }, width: number, height: number, clear = 10) {
  const dx = ends.x2 - ends.x1, dy = ends.y2 - ends.y1, len = Math.hypot(dx, dy) || 1;
  let nx = -dy / len, ny = dx / len; // a normal to the line
  if (ny > 0 || (ny === 0 && nx > 0)) { nx = -nx; ny = -ny; } // prefer above, then to the left (vertical links are on the right edge)
  const push = (Math.abs(nx) * width) / 2 + (Math.abs(ny) * height) / 2 + clear;
  return { x: (ends.x1 + ends.x2) / 2 + nx * push, y: (ends.y1 + ends.y2) / 2 + ny * push };
}
