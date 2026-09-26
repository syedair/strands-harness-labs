// The Settings page's knowledge bases: folders of markdown the assistant recalls from, read-only.
export type KnowledgeBase = {
  id: string; path: string; folders: string[] | null; files: number; sections: number; embedded: boolean; indexed_at: number;
};

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function ago(ms: number): string {
  if (ms < 60_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)} min ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)} h ago`;
  return `${Math.floor(ms / 86_400_000)} d ago`;
}

export function baseSummary(base: KnowledgeBase, now: number): string {
  const parts = [plural(base.files, "file"), plural(base.sections, "section"), `indexed ${ago(now - base.indexed_at)}`];
  if (!base.embedded) parts.push("not embedded (ollama pull nomic-embed-text)");
  return parts.join(" · ");
}
