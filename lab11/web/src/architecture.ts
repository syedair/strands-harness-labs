// The "How it works" walkthrough: the app's parts, and one turn as a list of steps between them. Pure data.

export type Tone = "plain" | "s1" | "llm" | "save";
export type ArchNode = { id: string; label: string; detail: string; x: number; y: number; tone: Tone; inHarness?: boolean; labelAbove?: boolean };
export type Step = { from: string; to: string; back?: boolean; label: string; title: string; text: string; example?: string; tone: Tone };

export const VIEW = { width: 1400, height: 530 };
export const NODE_R = 34; // each part is an icon in a circle of this radius
export const HARNESS = { x: 452, y: 40, width: 556, height: 466 }; // the Strands Harness, around its parts

export const NODES: ArchNode[] = [
  { id: "browser", label: "You", detail: "chat in the browser", x: 96, y: 190, tone: "plain" },
  { id: "server", label: "App server", detail: "FastAPI, streams events", x: 330, y: 190, tone: "plain" },
  { id: "agent", label: "Agent", detail: "orchestrates every step", x: 730, y: 190, tone: "plain", inHarness: true, labelAbove: true }, // links leave downwards
  { id: "session", label: "Session", detail: "chat history on disk", x: 548, y: 420, tone: "plain", inHarness: true },
  { id: "memory", label: "Memory", detail: "markdown notes", x: 730, y: 420, tone: "plain", inHarness: true },
  { id: "skills", label: "Skills", detail: "packing-list, yours…", x: 912, y: 420, tone: "plain", inHarness: true },
  { id: "system1", label: "System 1", detail: "Qwen · Jev · Kev · Laya", x: 1236, y: 80, tone: "s1" },
  { id: "llm", label: "LLM", detail: "Kimi K2.5 on Bedrock", x: 1236, y: 250, tone: "llm" },
  { id: "tools", label: "Tools", detail: "web_fetch · read · MCP", x: 1236, y: 420, tone: "plain" },
];

export const STEPS: Step[] = [
  { from: "browser", to: "server", label: "message", tone: "plain", title: "You send a message",
    text: "The browser posts your message to the app server and keeps the connection open for the reply.",
    example: "Pack for 4 days in Istanbul" },
  { from: "server", to: "agent", label: "message", tone: "plain", title: "The server hands it to the Agent",
    text: "Each chat has its own Agent. From here on, the Agent orchestrates every step and decides what happens next." },
  { from: "agent", to: "session", back: true, label: "history", tone: "plain", title: "The Agent restores the chat",
    text: "Sends the chat's id to the session. Gets back the conversation so far, saved on disk." },
  { from: "agent", to: "memory", back: true, label: "search", tone: "plain", title: "The Agent searches memory",
    text: "Sends the message to the memory store. Gets back every note that shares a word with it, relevant or not." },
  { from: "agent", to: "system1", back: true, label: "which notes help?", tone: "s1", title: "The Agent asks System 1 which notes help",
    text: "Sends each note with one yes/no question. Gets back a probability per note; notes at 0.5 or above are kept, best 5. The memory core fires.",
    example: "Would this fact help answer the message? · Trip to Istanbul in March → 0.91 · Favourite airline → 0.08" },
  { from: "agent", to: "llm", back: true, label: "message + notes", tone: "llm", title: "The Agent asks the LLM for a plan",
    text: "Sends the message with the recalled notes. Gets back a request to load the packing-list skill." },
  { from: "agent", to: "skills", back: true, label: "packing-list", tone: "plain", title: "The Agent loads the skill",
    text: "Sends the skill's name. Gets back its instructions: check the forecast, then list what to pack." },
  { from: "agent", to: "llm", back: true, label: "skill", tone: "llm", title: "The Agent passes the skill to the LLM",
    text: "Sends the skill's instructions. Gets back a tool call: fetch Istanbul's forecast.",
    example: "web_fetch https://wttr.in/Istanbul?format=3" },
  { from: "agent", to: "system1", back: true, label: "allow the tool?", tone: "s1", title: "The Agent asks System 1 to gate the tool",
    text: "The tool gate is a harness intervention on before_tool_call. Sends the call with two questions. Gets back probabilities that Python turns into Proceed, Guide or Deny.",
    example: "Is this a sensible step towards answering? 0.99 · Did the user mention this city? 0.97 → Proceed" },
  { from: "agent", to: "tools", back: true, label: "web_fetch", tone: "plain", title: "The Agent runs the tool",
    text: "Sends the allowed call. Gets back the forecast. Connectors you turn on add their MCP tools here.",
    example: "Istanbul: ☁️ +22°C" },
  { from: "agent", to: "llm", back: true, label: "forecast", tone: "llm", title: "The Agent asks the LLM for the answer",
    text: "Sends the forecast, after searching and checking memory again. Gets back the packing list." },
  { from: "agent", to: "system1", back: true, label: "complete?", tone: "s1", title: "The Agent asks System 1 to check the answer",
    text: "The completion check is a harness intervention on after_model_call, for multi-part requests. Sends the answer with one question. Gets back a probability; a half answer goes back to the LLM, up to twice." },
  { from: "agent", to: "server", label: "answer", tone: "plain", title: "The Agent returns the answer",
    text: "Sends the answer to the server, along with every step as an event: recalls, tool calls, gate and check decisions." },
  { from: "server", to: "browser", back: true, label: "stream", tone: "plain", title: "The server streams it to you",
    text: "Sends the answer as it's written, with the steps folded into one row above it. Keeps the connection open for one last step." },
  { from: "server", to: "agent", label: "save", tone: "save", title: "The server asks the Agent to remember",
    text: "Once the reply is out, the server asks the Agent to save what it learned." },
  { from: "agent", to: "memory", back: true, label: "new notes", tone: "save", title: "The Agent saves what it learned",
    text: "Sends the new facts from the conversation. Gets back dated notes, which gather in violet on the memory core.",
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

/** Where a link between two parts starts and ends: on the edge of their circles, not their centres. */
export function linkEnds(a: ArchNode, b: ArchNode, gap = 6) {
  const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
  const reach = (NODE_R + gap) / len;
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

const labelOf = new Map(NODES.map((n) => [n.id, n.label]));

/** A step's route as its arrow shows it: "Agent ⇄ System 1" for a round trip, "You → App server" for a hand-off. */
export const routeOf = (step: Step) => `${labelOf.get(step.from)} ${step.back ? "⇄" : "→"} ${labelOf.get(step.to)}`;
