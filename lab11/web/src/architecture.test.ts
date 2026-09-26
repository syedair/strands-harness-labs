import { describe, expect, it } from "vitest";
import { NODES, STEPS, linkEnds, sceneAt } from "./architecture";

describe("the architecture walkthrough", () => {
  it("starts with only the browser on screen", () => {
    const scene = sceneAt(-1);
    expect([...scene.shown]).toEqual(["browser"]);
    expect(scene.current).toBeNull();
  });

  it("brings each part in the first time a step uses it, and keeps it", () => {
    const first = sceneAt(0);
    expect(first.shown).toEqual(new Set(["browser", "server"]));
    const later = sceneAt(3);
    expect(later.shown.has("server") && later.shown.has("system1")).toBe(true);
    expect(later.shown.has("tools")).toBe(false);
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
