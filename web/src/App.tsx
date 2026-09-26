import { useEffect, useRef, useState } from "react";
import { fetchSystem1, sendMessage, type System1Option } from "./api";
import { applyEvent, newAssistantTurn, type Turn } from "./chat";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { Header } from "./components/Header";
import { Message } from "./components/Message";

export default function App() {
  const [options, setOptions] = useState<System1Option[]>([]);
  const [system1, setSystem1] = useState("ollama/qwen3.5:4b");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [serverDown, setServerDown] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const busy = turns.some((t) => t.role === "assistant" && t.streaming);

  useEffect(() => {
    fetchSystem1().then((r) => { setOptions(r.options); setSystem1(r.default); }).catch(() => setServerDown(true));
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" }); // braces: an effect must not return a value
  }, [turns]);

  async function send(text: string) {
    setTurns((t) => [...t, { role: "user", text }, newAssistantTurn()]);
    const update = (fn: (turn: Extract<Turn, { role: "assistant" }>) => Turn) =>
      setTurns((t) => [...t.slice(0, -1), fn(t[t.length - 1] as Extract<Turn, { role: "assistant" }>)]);
    try {
      for await (const event of sendMessage(sessionId, text, system1)) update((turn) => applyEvent(turn, event));
    } catch (error) {
      update((turn) => applyEvent(turn, { type: "error", message: String(error) }));
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col gap-4 px-6 py-6">
      <Header options={options} value={system1} onChange={setSystem1}
              onNewChat={() => { setTurns([]); setSessionId(crypto.randomUUID()); }} />
      {serverDown && (
        <p className="glass rounded-xl px-4 py-3 text-sm text-warn">
          Can't reach the server. Start it: <code className="font-mono">uv run --extra web labs/lab11_web_server.py</code>
        </p>
      )}
      <main className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {turns.length === 0 ? <EmptyState onPick={send} /> : turns.map((turn, i) => <Message key={i} turn={turn} />)}
        <div ref={bottom} />
      </main>
      <Composer disabled={busy || serverDown} onSend={send} />
    </div>
  );
}
