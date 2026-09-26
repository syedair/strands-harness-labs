import { ServerOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api";
import type { Chat, ChatSummary, Connector, FileInfo, Harness, MemoryGraph, Options } from "./api";
import { applyEvent, finishTurn, newAssistantTurn, statusOf, turnsFromHistory, type AssistantTurn, type Part, type Turn } from "./chat";
import { ComposerBar } from "./components/ComposerBar";
import { EmptyState } from "./components/EmptyState";
import { HarnessPanel } from "./components/HarnessPanel";
import { Architecture } from "./components/Architecture";
import { Header } from "./components/Header";
import { Message } from "./components/Message";
import type { Recall } from "./components/MemoryGlobe";
import { NO_BURST, NO_GHOSTS, type Burst, type Ghosts } from "./globe";
import type { Switching } from "./connectors";
import { Sidebar } from "./components/Sidebar";

const firstAvailable = (choices: api.Choice[], preferred: string) =>
  choices.find((c) => c.id === preferred && c.available)?.id ?? choices.find((c) => c.available)?.id ?? preferred;

export default function App() {
  const [options, setOptions] = useState<Options | null>(null);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [chat, setChat] = useState<Chat | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [model, setModel] = useState("");
  const [system1, setSystem1] = useState("");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [harness, setHarness] = useState<Harness | null>(null);
  const [memory, setMemory] = useState<MemoryGraph>({ nodes: [], links: [] });
  const [fired, setFired] = useState<Burst>(NO_BURST);
  const [stored, setStored] = useState<Burst>(NO_BURST);
  const [forgot, setForgot] = useState<Ghosts>(NO_GHOSTS);
  const memoryNow = useRef(memory); // the notes as they were before a forget deleted them
  memoryNow.current = memory;
  const dissolve = (ids: string[]) =>
    setForgot({ ids, at: Date.now(), nodes: memoryNow.current.nodes.filter((n) => ids.includes(n.id)) });
  const [recall, setRecall] = useState<Recall | null>(null);
  const [attached, setAttached] = useState<FileInfo[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [architecture, setArchitecture] = useState(false); // the "How it works" page instead of the chat
  const [serverDown, setServerDown] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const [switching, setSwitching] = useState<Switching>(null); // a connector starting or stopping
  const [sending, setSending] = useState(false); // from send until the stream closes (memory is saved after "done")
  const busy = sending || turns.some((t) => t.role === "assistant" && t.streaming);
  const last = turns[turns.length - 1];
  const status = last?.role === "assistant" ? statusOf(last) : "done";
  const coreState = status === "done" ? "idle" : status; // the memory core reacts to what the agent is doing
  const decisions = turns.flatMap((t) => (t.role === "assistant" ? t.parts : []))
    .filter((p): p is Extract<Part, { kind: "decision" }> => p.kind === "decision");

  const refresh = useCallback(async (chatId?: string) => {
    setChats(await api.listChats());
    setMemory(await api.fetchMemory());
    setHarness(await api.fetchHarness(chatId)); // no chat yet: what a new chat starts with
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const opts = await api.fetchOptions();
        setOptions(opts);
        setModel(firstAvailable(opts.models, opts.default_model));
        setSystem1(firstAvailable(opts.system1.options, opts.system1.default));
        setConnectors(await api.listConnectors());
        await refresh();
      } catch {
        setServerDown(true);
      }
    })();
  }, [refresh]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" }); // braces: an effect must not return a value
  }, [turns]);

  async function openChat(id: string) {
    if (busy) return; // the reply still streaming belongs to this chat
    const opened = await api.openChat(id);
    setChat(opened);
    setTurns(turnsFromHistory(opened.turns));
    if (options) {
      setModel(firstAvailable(options.models, opened.model));
      setSystem1(firstAvailable(options.system1.options, opened.system1_model));
    }
    setAttached([]);
    setFired(NO_BURST);
    setHarness(await api.fetchHarness(id));
  }

  async function newChat() {
    if (busy) return;
    setChat(null);
    setTurns([]);
    setAttached([]);
    setFired(NO_BURST);
    setHarness(await api.fetchHarness());
  }

  async function ensureChat(): Promise<string> {
    if (chat) return chat.id;
    const { id } = await api.createChat();
    const created = await api.openChat(id);
    setChat(created);
    return id;
  }

  async function send(text: string) {
    setSending(true);
    try {
      await stream(text);
    } finally {
      setSending(false);
    }
  }

  async function stream(text: string) {
    const chatId = await ensureChat();
    setTurns((t) => [...t, { role: "user", text }, newAssistantTurn()]);
    setAttached([]);
    const update = (fn: (turn: AssistantTurn) => AssistantTurn) =>
      setTurns((t) => [...t.slice(0, -1), fn(t[t.length - 1] as AssistantTurn)]);
    try {
      for await (const event of api.sendMessage(chatId, text, model, system1)) {
        if (event.type === "title") setChat((c) => (c ? { ...c, title: event.title } : c));
        if (event.type === "memory") { setFired({ ids: event.ids, at: Date.now() }); setRecall(event); }
        if (event.type === "stored") setStored({ ids: event.ids, at: Date.now() });
        if (event.type === "forgot") dissolve(event.ids);
        update((turn) => applyEvent(turn, event));
      }
    } catch (error) {
      update((turn) => applyEvent(turn, { type: "error", message: String(error) }));
    }
    update(finishTurn);
    await refresh(chatId); // the stream closes after memory is saved, so this sees new notes
  }

  async function attach(file: File) {
    try {
      const chatId = await ensureChat();
      const info = await api.uploadFile(chatId, file);
      setAttached((a) => [...a.filter((f) => f.name !== info.name), info]);
    } catch (error) {
      setTurns((t) => [...t, { role: "assistant", parts: [], streaming: false, error: String(error) }]);
    }
  }

  async function toggleConnector(id: string, on: boolean) {
    if (switching) return;
    setSwitching({ id, on });
    try {
      const chatId = await ensureChat();
      const enabled = on ? [...(harness?.connectors.enabled ?? []), id] : (harness?.connectors.enabled ?? []).filter((c) => c !== id);
      await api.setConnectors(chatId, enabled);
      setHarness(await api.fetchHarness(chatId)); // starting an MCP server can take a few seconds
    } finally {
      setSwitching(null);
    }
  }

  async function addSkill(file: File) {
    await api.uploadSkill(file); // errors show in the Skills tab
    setHarness(await api.fetchHarness(chat?.id));
  }

  async function addConnector(label: string, command: string, args: string[]) {
    await api.addConnector(label, command, args);
    setConnectors(await api.listConnectors());
  }

  async function forget(id: string) {
    await api.forgetMemory(id);
    dissolve([id]);
    setMemory(await api.fetchMemory());
  }

  async function removeChat(id: string) {
    await api.deleteChat(id);
    if (chat?.id === id) await newChat();
    await refresh();
  }

  return (
    <div className="flex h-screen">
      <Sidebar chats={chats} activeId={chat?.id ?? null} busy={busy} onOpen={openChat} onNew={newChat} onDelete={removeChat} />
      <div className="flex min-w-0 flex-1 flex-col gap-4 px-6 py-6">
        <Header title={chat?.title && chat.title !== "New chat" ? chat.title : "Travel assistant"} onTogglePanel={() => setPanelOpen(!panelOpen)}
                showingArchitecture={architecture} onToggleArchitecture={() => setArchitecture(!architecture)} />
        {serverDown && (
          <p className="glass flex items-center gap-2 rounded-xl px-4 py-3 text-sm text-warn">
            <ServerOff size={16} /> Can't reach the server. Start it: <code className="font-mono">uv run --extra web lab11/server/app.py</code>
          </p>
        )}
        {architecture ? <Architecture /> : <>
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto">
          {turns.length === 0 ? <EmptyState onPick={send} /> : turns.map((turn, i) => <Message key={i} turn={turn} />)}
          <div ref={bottom} />
        </main>
        <div className="mx-auto w-full max-w-3xl">
          <ComposerBar busy={busy} disabled={serverDown || !options}
                       models={options?.models ?? []} model={model} onModel={setModel}
                       system1={options?.system1.options ?? []} system1Model={system1} onSystem1={setSystem1}
                       connectors={connectors} enabledConnectors={harness?.connectors.enabled ?? []}
                       connectorErrors={harness?.connectors.errors ?? []}
                       switching={switching} onToggleConnector={toggleConnector} onAddConnector={addConnector}
                       attached={attached} onAttach={attach}
                       onSend={send} />
        </div>
        </>}
      </div>
      {!architecture && (
      <div className={`${panelOpen ? "fixed inset-y-0 right-0 z-30 bg-bg-1/95 backdrop-blur" : "hidden"} lg:static lg:block`}>
        <HarnessPanel harness={harness} connectors={connectors} switching={switching} onAddSkill={addSkill} onToggleConnector={toggleConnector} memory={memory} fired={fired} stored={stored} forgot={forgot} recall={recall} decisions={decisions} state={coreState} onForget={forget} />
      </div>
      )}
    </div>
  );
}
