// Talks to labs/lab11_web_server.py. The chat reply arrives as one JSON event per line.
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
  | { type: "done" }
  | { type: "error"; message: string };

export type System1Option = { id: string; label: string; available: boolean; reason: string | null };
export type System1Response = { default: string; options: System1Option[] };

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

export async function* sendMessage(sessionId: string, message: string, system1Model: string): AsyncGenerator<ChatEvent> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, system1_model: system1Model }),
  });
  if (!response.ok || !response.body) throw new Error(`Server error ${response.status}`);
  yield* readEvents(response.body);
}

export async function fetchSystem1(): Promise<System1Response> {
  const response = await fetch("/api/system1");
  if (!response.ok) throw new Error(`Server error ${response.status}`);
  return response.json();
}
