// Memory notes -> the core's stars and links, brain-style. Pure, so it's easy to test.
//   fired  = recalled this turn
//   primed = linked to a fired note (activation spreads one hop, like associations in the brain)
//   links: cofire (both ends fired) · spread (one end fired) · idle
//   strength = similarity + how often the two were recalled together (fire together, wire together)
import type { MemoryGraph } from "./api";

export type NodeState = "fired" | "primed" | "idle";
export type LinkState = "cofire" | "spread" | "idle";
export type GlobeNode = { id: string; text: string; hits: number; created: number; state: NodeState; val: number };
export type GlobeLink = { source: string; target: string; weight: number; together: number; state: LinkState; strength: number };

export function toGraph(graph: MemoryGraph, fired: string[]): { nodes: GlobeNode[]; links: GlobeLink[] } {
  const hot = new Set(fired);
  const primed = new Set<string>();
  for (const l of graph.links) {
    if (hot.has(l.source) && !hot.has(l.target)) primed.add(l.target);
    if (hot.has(l.target) && !hot.has(l.source)) primed.add(l.source);
  }
  return {
    // val is the star's size: notes recalled more often grow
    nodes: graph.nodes.map((n) => ({
      ...n, val: 1 + Math.log2(1 + n.hits) * 2,
      state: hot.has(n.id) ? "fired" : primed.has(n.id) ? "primed" : "idle",
    })),
    links: graph.links.map((l) => {
      const ends = Number(hot.has(l.source)) + Number(hot.has(l.target));
      return { ...l, state: ends === 2 ? "cofire" : ends === 1 ? "spread" : "idle", strength: l.weight + Math.log2(1 + l.together) };
    }),
  };
}

/** Particles for the memory core: a ball, denser towards the centre so the core glows. */
export function cloudPoints(n: number, radius: number, random: () => number = Math.random) {
  return Array.from({ length: n }, () => {
    const u = random() * 2 - 1; // a random direction on the sphere
    const angle = random() * Math.PI * 2;
    const ring = Math.sqrt(1 - u * u);
    const r = radius * Math.pow(random(), 0.75); // below 1/3 power: more points near the centre
    return { x: Math.cos(angle) * ring * r, y: u * r, z: Math.sin(angle) * ring * r };
  });
}

/** A recall or a save: which notes, and when it happened. */
export type Burst = { ids: string[]; at: number };
export const SHOW_MS = 6000; // how long a recall or a save keeps animating
export const NO_BURST: Burst = { ids: [], at: 0 };

/** How much longer a burst should animate; 0 once it's over (so reopening the tab doesn't replay it). */
export function showingFor(burst: Burst, now: number): number {
  return burst.ids.length === 0 ? 0 : Math.max(0, SHOW_MS - (now - burst.at));
}

/** Notes being forgotten: already deleted on disk, kept in the picture while they dissolve. */
export type Ghosts = Burst & { nodes: MemoryGraph["nodes"] };
export const NO_GHOSTS: Ghosts = { ...NO_BURST, nodes: [] };

export function withGhosts(graph: MemoryGraph, ghosts: MemoryGraph["nodes"], active: string[]): MemoryGraph {
  const present = new Set(graph.nodes.map((n) => n.id));
  const extra = ghosts.filter((n) => active.includes(n.id) && !present.has(n.id));
  return extra.length ? { ...graph, nodes: [...graph.nodes, ...extra] } : graph;
}

/** Where a note sits on the sphere, from its id alone: forgetting or saving others never moves it. */
export function notePoint(id: string, radius: number): { x: number; y: number; z: number } {
  let h = 2166136261; // FNV-1a hash of the id, split into two numbers in [0, 1)
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  const u = ((h >>> 0) & 0xffff) / 0x10000, v = ((h >>> 16) & 0xffff) / 0x10000;
  const y = 1 - 2 * u, ring = Math.sqrt(1 - y * y), angle = 2 * Math.PI * v;
  return { x: Math.cos(angle) * ring * radius, y: y * radius, z: Math.sin(angle) * ring * radius };
}

/** How big and bright stars and links are drawn for this many notes: unchanged up to 30, thinner beyond. */
export function density(count: number): { star: number; glow: number; link: number } {
  const f = Math.min(1, Math.sqrt(30 / Math.max(count, 1)));
  return { star: Math.max(0.4, f ** 0.7), glow: Math.max(0.4, Math.sqrt(f)), link: Math.max(0.15, f) };
}

/** Notes from KNOWLEDGE_DIR have ids starting "kb:"; everything else is a memory. */
export const isKnowledge = (id: string) => id.startsWith("kb:");

export function recallLabel(ids: string[]): string {
  const notes = ids.filter(isKnowledge).length, memories = ids.length - notes;
  const parts = [];
  if (memories) parts.push(`${memories} ${memories === 1 ? "memory" : "memories"}`);
  if (notes) parts.push(`${notes} ${notes === 1 ? "note" : "notes"}`);
  return parts.join(", ");
}

/** The user's memories without the knowledge sections, for the list and Clear all. */
export const memoriesOnly = (graph: MemoryGraph) => graph.nodes.filter((n) => n.kind !== "knowledge");
