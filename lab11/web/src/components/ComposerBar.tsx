import { Cpu, FileText, LoaderCircle, Paperclip, SendHorizontal, Sparkles } from "lucide-react";
import { useRef, useState } from "react";
import type { Choice, Connector, FileInfo } from "../api";
import type { Switching } from "../connectors";
import { ConnectorsMenu } from "./ConnectorsMenu";
import { Picker } from "./Picker";

type Props = {
  busy: boolean;
  disabled: boolean;
  models: Choice[];
  model: string;
  onModel: (id: string) => void;
  system1: Choice[];
  system1Model: string;
  onSystem1: (id: string) => void;
  connectors: Connector[];
  enabledConnectors: string[];
  connectorErrors: { id: string; error: string }[];
  switching: Switching;
  onToggleConnector: (id: string, on: boolean) => void;
  onAddConnector: (label: string, command: string, args: string[]) => void;
  attached: FileInfo[];
  onAttach: (file: File) => void;
  onSend: (text: string) => void;
};

export function ComposerBar(props: Props) {
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const blocked = props.busy || props.disabled;
  const send = () => {
    if (!text.trim() || blocked) return;
    props.onSend(text.trim());
    setText("");
  };
  return (
    <div className="glass tint space-y-2 rounded-2xl p-3 transition focus-within:shadow-[0_0_0_4px_rgba(110,231,183,0.15)]">
      {props.attached.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {props.attached.map((f) => (
            <span key={f.name} className="animate-rise flex items-center gap-1.5 rounded-lg bg-black/30 px-2 py-1 text-xs">
              <FileText size={13} className="text-accent-2" /> {f.name}
              <span className="text-ink-2">· sent with your next message</span>
            </span>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2">
        <button aria-label="Attach a file" onClick={() => fileInput.current?.click()} disabled={props.disabled}
                className="press flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-ink-2 hover:bg-white/10 hover:text-ink disabled:opacity-40">
          <Paperclip size={18} />
        </button>
        <input ref={fileInput} type="file" hidden accept=".txt,.md,.csv,.json,.pdf"
               onChange={(e) => { const f = e.target.files?.[0]; if (f) props.onAttach(f); e.target.value = ""; }} />
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={1} placeholder="Ask about a trip…"
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  className="flex-1 resize-none bg-transparent py-2 text-ink outline-none placeholder:text-ink-2" />
        <button onClick={send} disabled={blocked || !text.trim()} aria-label="Send"
                className="press flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-bg-1 hover:brightness-110 disabled:opacity-40">
          {props.busy ? <LoaderCircle size={18} className="animate-spin" /> : <SendHorizontal size={18} />}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Picker label="Language model" icon={Sparkles} choices={props.models} value={props.model} onChange={props.onModel} />
        <Picker label="System 1 model" icon={Cpu} choices={props.system1} value={props.system1Model} onChange={props.onSystem1} />
        <ConnectorsMenu connectors={props.connectors} enabled={props.enabledConnectors} errors={props.connectorErrors} switching={props.switching}
                        onToggle={props.onToggleConnector} onAdd={props.onAddConnector} />
      </div>
    </div>
  );
}
