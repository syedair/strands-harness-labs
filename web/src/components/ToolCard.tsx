export function ToolCard({ name, input }: { name: string; input: Record<string, unknown> }) {
  const target = typeof input.url === "string" ? input.url.replace(/^https?:\/\//, "") : JSON.stringify(input);
  return (
    <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 font-mono text-xs text-ink-2">
      <span className="text-accent-2">{name}</span>
      <span className="truncate">{target}</span>
    </div>
  );
}
