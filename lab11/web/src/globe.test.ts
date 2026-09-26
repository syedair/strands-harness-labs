import { describe, expect, it } from "vitest";
import { cloudPoints, spherePoint, toGraph } from "./globe";

const api = {
  nodes: [
    { id: "home.md", text: "The user lives in Dubai.", hits: 3, created: 3 },
    { id: "trip.md", text: "Trip to Istanbul in March.", hits: 0, created: 2 },
    { id: "food.md", text: "Likes street food.", hits: 1, created: 1 },
  ],
  links: [
    { source: "home.md", target: "trip.md", weight: 0.8 },
    { source: "trip.md", target: "food.md", weight: 0.7 },
  ],
};

describe("toGraph", () => {
  it("fires the recalled notes and every link touching them", () => {
    const g = toGraph(api, ["home.md"]);
    expect(g.nodes.find((n) => n.id === "home.md")?.fired).toBe(true);
    expect(g.nodes.find((n) => n.id === "trip.md")?.fired).toBe(false);
    expect(g.links.map((l) => l.fired)).toEqual([true, false]);
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

describe("spherePoint", () => {
  it("puts every note on the globe's surface", () => {
    for (let i = 0; i < 7; i++) {
      const { x, y, z } = spherePoint(i, 7, 50);
      expect(Math.hypot(x, y, z)).toBeCloseTo(50, 5);
    }
  });

  it("spreads notes apart instead of stacking them", () => {
    const a = spherePoint(0, 7, 50), b = spherePoint(1, 7, 50);
    expect(Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)).toBeGreaterThan(20);
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
