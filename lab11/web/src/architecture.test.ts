import { describe, expect, it } from "vitest";
import { NODES, NODE_R, STEPS, endOf, labelSpot, linkEnds, routeOf, sceneAt } from "./architecture";

describe("the architecture walkthrough", () => {
  it("starts with only the browser on screen", () => {
    const scene = sceneAt(-1);
    expect([...scene.shown]).toEqual(["browser"]);
    expect(scene.current).toBeNull();
  });

  it("brings each part in the first time a step uses it, and keeps it", () => {
    const first = sceneAt(0);
    expect(first.shown).toEqual(new Set(["browser", "server"]));
    const later = sceneAt(4); // System 1 joins at step 5
    expect(later.shown.has("server") && later.shown.has("system1")).toBe(true);
    expect(later.shown.has("tools")).toBe(false);
    expect(sceneAt(3).shown.has("system1")).toBe(false);
  });

  it("lights the current step's link and dims the ones before it", () => {
    const scene = sceneAt(2);
    expect(scene.current).toEqual(STEPS[2]);
    expect(scene.past).toEqual([STEPS[0], STEPS[1]]);
  });

  it("only links parts that exist, and ends with everything shown", () => {
    const ids = new Set(NODES.map((n) => n.id));
    for (const step of STEPS) expect(ids.has(step.from) && ids.has(step.to)).toBe(true);
    expect(sceneAt(STEPS.length - 1).shown.size).toBe(NODES.length);
  });

  it("clamps steps past either end", () => {
    expect(sceneAt(99).current).toEqual(STEPS[STEPS.length - 1]);
    expect(sceneAt(-5).current).toBeNull();
  });
});

describe("the diagram's layout", () => {
  it("leaves every link long enough to see its arrow", () => {
    const at = new Map(NODES.map((n) => [n.id, n]));
    for (const step of STEPS) {
      const { x1, y1, x2, y2 } = linkEnds(at.get(step.from)!, at.get(step.to)!);
      expect(Math.hypot(x2 - x1, y2 - y1), `${step.from} → ${step.to}`).toBeGreaterThanOrEqual(44);
    }
  });
});

describe("labelSpot", () => {
  // how far the label's box stays from the (infinite) line through the link, in any direction
  const clearance = (x1: number, y1: number, x2: number, y2: number, w: number, h: number) => {
    const spot = labelSpot({ x1, y1, x2, y2 }, w, h);
    const len = Math.hypot(x2 - x1, y2 - y1), nx = -(y2 - y1) / len, ny = (x2 - x1) / len;
    const centre = Math.abs((spot.x - x1) * nx + (spot.y - y1) * ny);
    return centre - (Math.abs(nx) * w) / 2 - (Math.abs(ny) * h) / 2;
  };

  it("keeps the label clear of its line whatever the angle", () => {
    expect(clearance(0, 0, 120, 0, 70, 22)).toBeGreaterThanOrEqual(8); // horizontal
    expect(clearance(0, 0, 0, 120, 70, 22)).toBeGreaterThanOrEqual(8); // vertical
    expect(clearance(0, 0, 90, -140, 90, 22)).toBeGreaterThanOrEqual(8); // diagonal
  });
});

describe("the sequence", () => {
  it("starts every step where the previous one ended", () => {
    for (let i = 1; i < STEPS.length; i++) {
      expect(STEPS[i].from, `step ${i + 1}: ${STEPS[i].title}`).toBe(endOf(STEPS[i - 1]));
    }
  });

  it("puts the Agent at the centre: every step touches it or the app server", () => {
    for (const s of STEPS) expect([s.from, s.to].some((id) => id === "agent" || id === "server")).toBe(true);
  });

  it("round trips end back where they started", () => {
    expect(endOf({ ...STEPS[0], back: true })).toBe(STEPS[0].from);
    expect(endOf({ ...STEPS[0], back: false })).toBe(STEPS[0].to);
  });
});

describe("routeOf", () => {
  it("names a step's route the way its arrow is drawn", () => {
    expect(routeOf(STEPS[0])).toBe("You → App server");
    expect(routeOf(STEPS[4])).toBe("Agent ⇄ System 1");
  });
});

describe("icon nodes", () => {
  it("attach links to the edge of each icon's circle", () => {
    const [a, b] = [NODES[0], NODES[1]];
    const { x1, y1, x2, y2 } = linkEnds(a, b, 6);
    expect(Math.hypot(x1 - a.x, y1 - a.y)).toBeCloseTo(NODE_R + 6);
    expect(Math.hypot(x2 - b.x, y2 - b.y)).toBeCloseTo(NODE_R + 6);
  });
});
