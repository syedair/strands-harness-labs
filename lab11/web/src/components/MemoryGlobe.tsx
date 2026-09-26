// Placeholder list until the 3D globe (task 8).
import type { MemoryGraph } from "../api";

export default function MemoryGlobe({ graph, fired }: { graph: MemoryGraph; fired: string[] }) {
  if (graph.nodes.length === 0) return <p className="text-ink-2">No memories yet — tell the assistant something about you.</p>;
  return (
    <ul className="space-y-1.5">
      {graph.nodes.map((n) => (
        <li key={n.id} className={`rounded-lg px-3 py-2 ${fired.includes(n.id) ? "bg-accent/15 text-accent" : "bg-black/20"}`}>{n.text}</li>
      ))}
    </ul>
  );
}
