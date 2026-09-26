// Settings: the folders of markdown (an Obsidian vault works) the assistant recalls from, read-only.
import { FolderPlus, LibraryBig, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import * as api from "../api";
import { baseSummary, type KnowledgeBase } from "../knowledge";
import { ConfirmButton } from "./ConfirmButton";

export function Settings({ onChanged }: { onChanged: () => void }) {
  const [bases, setBases] = useState<KnowledgeBase[] | null>(null);
  const [path, setPath] = useState("");
  const [folders, setFolders] = useState("");
  const [working, setWorking] = useState<string | null>(null); // "add" or the id being re-indexed
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.listKnowledge().then(setBases).catch((e) => setError(String(e))); }, []);

  async function run(what: string, action: () => Promise<unknown>) {
    setWorking(what);
    setError(null);
    try {
      await action();
      setBases(await api.listKnowledge());
      onChanged(); // the memory core shows the new sections
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setWorking(null);
    }
  }

  const add = () => run("add", async () => {
    const only = folders.split(",").map((f) => f.trim()).filter(Boolean);
    await api.addKnowledge(path.trim(), only.length ? only : null);
    setPath("");
    setFolders("");
  });

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-5 overflow-y-auto">
      <section className="glass space-y-4 rounded-2xl p-5">
        <div className="flex items-center gap-2">
          <LibraryBig size={18} className="text-accent" />
          <h2 className="font-display text-lg font-semibold">Knowledge bases</h2>
        </div>
        <p className="max-w-[65ch] text-sm text-ink-2">
          Folders of markdown notes the assistant recalls from, like an Obsidian vault. Files at any depth are split
          into sections and indexed. The app only reads them: it never writes into these folders. When a section is
          recalled, its text is sent to the language model, and to System 1 when that model is hosted (Jev).
        </p>

        {bases === null ? <p className="text-sm text-ink-2">Loading…</p> : bases.length === 0 ? (
          <p className="rounded-xl border border-dashed border-white/15 px-4 py-3 text-sm text-ink-2">No knowledge bases yet. Add a folder below.</p>
        ) : (
          <ul className="space-y-2">
            {bases.map((b) => (
              <li key={b.id} className="grid gap-3 rounded-xl bg-black/20 px-4 py-3 sm:grid-cols-[1fr_auto] sm:items-center">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm">{b.path}</p>
                  <p className={`text-xs ${b.embedded ? "text-ink-2" : "text-warn"}`}>{baseSummary(b, Date.now())}</p>
                  {b.folders && <p className="text-xs text-ink-2">Only: {b.folders.join(", ")}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => run(b.id, () => api.reindexKnowledge(b.id))} disabled={working !== null}
                          className="press flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1.5 text-xs text-ink-2 hover:text-ink disabled:opacity-40">
                    <RefreshCw size={13} className={working === b.id ? "animate-spin text-accent" : ""} /> {working === b.id ? "Indexing…" : "Re-index"}
                  </button>
                  <div className="w-44">
                    <ConfirmButton label="Remove" question="Remove? (files stay)" disabled={working !== null}
                                   onConfirm={() => run(`remove-${b.id}`, () => api.removeKnowledge(b.id))} />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}

        <form className="grid gap-2 sm:grid-cols-[1fr_14rem_auto]" onSubmit={(e) => { e.preventDefault(); add(); }}>
          <input id="knowledge-path" required value={path} onChange={(e) => setPath(e.target.value)} disabled={working !== null}
                 placeholder="~/Documents/Obsidian/My Vault" aria-label="Folder path"
                 className="rounded-xl border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm outline-none focus:border-accent/60" />
          <input id="knowledge-folders" value={folders} onChange={(e) => setFolders(e.target.value)} disabled={working !== null}
                 placeholder="Only these folders (optional)" aria-label="Only these top-level folders, comma-separated"
                 className="rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm outline-none focus:border-accent/60" />
          <button type="submit" disabled={working !== null || !path.trim()}
                  className="press flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-bg-1 hover:brightness-110 disabled:opacity-40">
            {working === "add" ? <LoaderCircle size={15} className="animate-spin" /> : <FolderPlus size={15} />}
            {working === "add" ? "Indexing…" : "Add and index"}
          </button>
        </form>
        {error && <p className="text-sm text-warn">{error}</p>}
      </section>
    </div>
  );
}
