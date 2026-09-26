import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { disposeTree, setPositions } from "./dispose";

describe("disposeTree", () => {
  it("frees every geometry and material under an object and empties it", () => {
    const freed: string[] = [];
    const group = new THREE.Group();
    const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial());
    const star = new THREE.Sprite(new THREE.SpriteMaterial());
    line.geometry.addEventListener("dispose", () => freed.push("line geometry"));
    (line.material as THREE.Material).addEventListener("dispose", () => freed.push("line material"));
    star.material.addEventListener("dispose", () => freed.push("star material"));
    group.add(line, star);
    disposeTree(group);
    expect(freed.sort()).toEqual(["line geometry", "line material", "star material"]);
    expect(group.children).toHaveLength(0);
  });
});

describe("setPositions", () => {
  it("reuses one buffer frame after frame and draws only the points it was given", () => {
    const geometry = new THREE.BufferGeometry();
    setPositions(geometry, [1, 2, 3, 4, 5, 6]);
    const buffer = geometry.getAttribute("position");
    setPositions(geometry, [7, 8, 9]);
    expect(geometry.getAttribute("position")).toBe(buffer);
    expect(geometry.drawRange.count).toBe(1);
    expect(Array.from((buffer.array as Float32Array).slice(0, 3))).toEqual([7, 8, 9]);
  });
});
