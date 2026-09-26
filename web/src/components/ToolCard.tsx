import { BookOpen, Globe, Wrench } from "lucide-react";

const ICONS = { web_fetch: Globe, skills: BookOpen };

export function ToolCard({ name, input }: { name: string; input: Record<string, unknown> }) {
  const Icon = ICONS[name as keyof typeof ICONS] ?? Wrench;
  const target =
    typeof input.url === "string" ? input.url.replace(/^https?:\/\//, "")
    : typeof input.skill_name === "string" ? input.skill_name
    : JSON.stringify(input);
  return (
    <div className="animate-rise flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 font-mono text-xs text-ink-2">
      <Icon size={14} className="shrink-0 text-accent-2" />
      <span className="text-accent-2">{name}</span>
      <span className="truncate">{target}</span>
    </div>
  );
}
