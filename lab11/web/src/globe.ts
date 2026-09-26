// Memory notes -> the 3D graph's nodes and links. Pure, so it's easy to test.
import type { MemoryGraph } from "./api";

export type GlobeNode = { id: string; text: string; hits: number; fired: boolean; val: number };
export type GlobeLink = { source: string; target: string; weight: number; fired: boolean };

export function toGraph(graph: MemoryGraph, fired: string[]): { nodes: GlobeNode[]; links: GlobeLink[] } {
  const hot = new Set(fired);
  return {
    // val is the sphere's volume: notes recalled more often grow
    nodes: graph.nodes.map((n) => ({ ...n, fired: hot.has(n.id), val: 1 + Math.log2(1 + n.hits) * 2 })),
    links: graph.links.map((l) => ({ ...l, fired: hot.has(l.source) || hot.has(l.target) })),
  };
}

/** Point i of n spread evenly over a sphere (a Fibonacci spiral), so notes sit on a globe. */
export function spherePoint(i: number, n: number, radius: number): { x: number; y: number; z: number } {
  const y = n === 1 ? 0 : 1 - (2 * i) / (n - 1); // from the top of the globe to the bottom
  const ring = Math.sqrt(1 - y * y);
  const angle = i * Math.PI * (3 - Math.sqrt(5)); // the golden angle
  return { x: Math.cos(angle) * ring * radius, y: y * radius, z: Math.sin(angle) * ring * radius };
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
