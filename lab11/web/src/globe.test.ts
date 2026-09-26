import { describe, expect, it } from "vitest";
import { cloudPoints, notePoint, showingFor, toGraph, withGhosts } from "./globe";

const api = {
  nodes: [
    { id: "home.md", text: "The user lives in Dubai.", hits: 3, created: 3 },
    { id: "trip.md", text: "Trip to Istanbul in March.", hits: 0, created: 2 },
    { id: "food.md", text: "Likes street food.", hits: 1, created: 1 },
  ],
  links: [
    { source: "home.md", target: "trip.md", weight: 0.8, together: 0 },
    { source: "trip.md", target: "food.md", weight: 0.7, together: 0 },
  ],
};

describe("toGraph", () => {
  it("fires recalled notes and primes their neighbours (spreading activation)", () => {
    const g = toGraph(api, ["home.md"]);
    const state = (id: string) => g.nodes.find((n) => n.id === id)?.state;
    expect(state("home.md")).toBe("fired");
    expect(state("trip.md")).toBe("primed"); // linked to a recalled note
    expect(state("food.md")).toBe("idle"); // two hops away: no activation
    expect(g.links.map((l) => l.state)).toEqual(["spread", "idle"]);
  });

  it("links between two recalled notes co-fire", () => {
    const g = toGraph(api, ["home.md", "trip.md"]);
    expect(g.links[0].state).toBe("cofire");
    expect(g.nodes.find((n) => n.id === "food.md")?.state).toBe("primed");
  });

  it("notes recalled together more often are wired more strongly", () => {
    const g = toGraph({ ...api, links: [
      { source: "home.md", target: "trip.md", weight: 0.7, together: 0 },
      { source: "trip.md", target: "food.md", weight: 0.7, together: 5 },
    ] }, []);
    expect(g.links[1].strength).toBeGreaterThan(g.links[0].strength);
  });

  it("sizes notes by how often they were recalled", () => {
    const g = toGraph(api, []);
    const size = (id: string) => g.nodes.find((n) => n.id === id)!.val;
    expect(size("home.md")).toBeGreaterThan(size("food.md"));
    expect(size("food.md")).toBeGreaterThan(size("trip.md"));
  });

  it("handles no memories", () => {
    expect(toGraph({ nodes: [], links: [] }, [])).toEqual({ nodes: [], links: [] });
  });
});

describe("cloudPoints", () => {
  const seeded = () => {
    let s = 42;
    return () => ((s = (s * 16807) % 2147483647) / 2147483647);
  };

  it("keeps every particle inside the core", () => {
    const pts = cloudPoints(500, 60, seeded());
    expect(pts).toHaveLength(500);
    for (const p of pts) expect(Math.hypot(p.x, p.y, p.z)).toBeLessThanOrEqual(60 + 1e-9);
  });

  it("is denser towards the centre", () => {
    const pts = cloudPoints(2000, 60, seeded());
    const inner = pts.filter((p) => Math.hypot(p.x, p.y, p.z) < 30).length;
    // a uniform ball would put 1/8 of the points inside half the radius
    expect(inner / pts.length).toBeGreaterThan(0.2);
  });
});

describe("showingFor", () => {
  it("counts down from when the recall happened, so reopening the tab doesn't replay it", () => {
    const burst = { ids: ["a"], at: 1000 };
    expect(showingFor(burst, 1000)).toBe(6000);
    expect(showingFor(burst, 5000)).toBe(2000);
    expect(showingFor(burst, 7000)).toBe(0);
    expect(showingFor({ ids: [], at: 1000 }, 1000)).toBe(0);
  });
});

describe("withGhosts", () => {
  const graph = { nodes: [{ id: "home.md", text: "Dubai", hits: 0, created: 2 }], links: [] };
  const ghost = { id: "name.md", text: "John", hits: 1, created: 1 };

  it("keeps forgotten notes in the picture while they dissolve", () => {
    expect(withGhosts(graph, [ghost], ["name.md"]).nodes.map((n) => n.id)).toEqual(["home.md", "name.md"]);
  });

  it("drops them once the animation is over, and never shows a note twice", () => {
    expect(withGhosts(graph, [ghost], []).nodes.map((n) => n.id)).toEqual(["home.md"]);
    expect(withGhosts(graph, [graph.nodes[0]], ["home.md"]).nodes).toHaveLength(1);
  });
});

describe("notePoint", () => {
  it("puts a note in the same place however many other notes there are", () => {
    expect(notePoint("name.md", 50)).toEqual(notePoint("name.md", 50));
    const p = notePoint("name.md", 50);
    expect(Math.hypot(p.x, p.y, p.z)).toBeCloseTo(50);
  });

  it("spreads different notes apart", () => {
    const a = notePoint("home.md", 50), b = notePoint("trip.md", 50);
    expect(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)).toBeGreaterThan(1);
  });
});
