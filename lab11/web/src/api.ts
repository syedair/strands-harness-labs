// Talks to lab11/server/app.py. A reply arrives as one JSON event per line.
export type ChatEvent =
  | { type: "text"; delta: string }
  | { type: "tool"; name: string; input: Record<string, unknown> }
  | {
      type: "decision";
      source: "gate" | "check";
      action: "guide" | "deny" | "proceed";
      why: string | null; // which rule fired, e.g. "ask the user instead of guessing"
      p: number | null; // the probability behind that rule
      probs: Record<string, number>;
    }
  | { type: "memory"; ids: string[]; scores: number[]; query: string } // notes recalled, how relevant, for what
  | { type: "stored"; ids: string[] } // notes the harness just saved
  | { type: "title"; title: string }
  | { type: "done" }
  | { type: "error"; message: string };

export type Choice = { id: string; label: string; available: boolean; reason: string | null };
export type Options = { models: Choice[]; default_model: string; system1: { options: Choice[]; default: string } };
export type ChatSummary = { id: string; title: string; updated_at: number };
export type SavedTurn = { role: "user" | "assistant"; text: string };
export type FileInfo = { name: string; path: string; size: number };
export type Chat = {
  id: string; title: string; turns: SavedTurn[]; model: string; system1_model: string;
  connectors: string[]; files: FileInfo[];
};
export type Connector = { id: string; label: string; description: string; custom: boolean };
export type Harness = {
  tools: string[];
  skills: { name: string; description: string }[];
  session: { id: string; model: string; system1_model: string; messages: number; files: FileInfo[] };
  connectors: { enabled: string[]; errors: { id: string; error: string }[] };
};
export type MemoryGraph = {
  nodes: { id: string; text: string; hits: number; created: number }[]; // newest first
  links: { source: string; target: string; weight: number; together: number }[]; // similarity + co-recall count
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Server error ${response.status}`);
  }
  return response.json();
}

const send = (url: string, method: string, body?: unknown) =>
  fetch(url, { method, headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined });

export const fetchOptions = () => fetch("/api/options").then((r) => json<Options>(r));
export const listChats = () => fetch("/api/chats").then((r) => json<ChatSummary[]>(r));
export const createChat = () => send("/api/chats", "POST").then((r) => json<{ id: string }>(r));
export const deleteChat = (id: string) => send(`/api/chats/${id}`, "DELETE").then((r) => json(r));
export const openChat = (id: string) => fetch(`/api/chats/${id}`).then((r) => json<Chat>(r));
export const fetchHarness = (id?: string) => fetch(id ? `/api/harness?chat_id=${id}` : "/api/harness").then((r) => json<Harness>(r));
export const listConnectors = () => fetch("/api/connectors").then((r) => json<Connector[]>(r));
export const addConnector = (label: string, command: string, args: string[]) =>
  send("/api/connectors", "POST", { label, command, args }).then((r) => json<{ id: string }>(r));
export const setConnectors = (id: string, enabled: string[]) =>
  send(`/api/chats/${id}/connectors`, "PUT", { enabled }).then((r) => json(r));
export const fetchMemory = () => fetch("/api/memory").then((r) => json<MemoryGraph>(r));
export const forgetMemory = (id: string) => send(`/api/memory/${encodeURIComponent(id)}`, "DELETE").then((r) => json(r));

export async function uploadFile(id: string, file: File): Promise<FileInfo> {
  const form = new FormData();
  form.append("file", file);
  return json<FileInfo>(await fetch(`/api/chats/${id}/files`, { method: "POST", body: form }));
}

export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }); // stream: keeps multi-byte characters intact
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // a partial line waits for the next chunk
    for (const line of lines) if (line.trim()) yield JSON.parse(line) as ChatEvent;
  }
  if (buffer.trim()) yield JSON.parse(buffer) as ChatEvent;
}

export async function* sendMessage(chatId: string, message: string, model: string, system1Model: string): AsyncGenerator<ChatEvent> {
  const response = await send(`/api/chats/${chatId}/messages`, "POST", { message, model, system1_model: system1Model });
  if (!response.ok || !response.body) throw new Error(`Server error ${response.status}`);
  yield* readEvents(response.body);
}
