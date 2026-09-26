// Free the GPU memory three.js holds for an object's children (it isn't garbage collected), then remove them.
import * as THREE from "three";

export function disposeTree(root: THREE.Object3D): void {
  root.traverse((node) => {
    if (node === root) return;
    const { geometry, material } = node as THREE.Mesh;
    if (geometry && !(node instanceof THREE.Sprite)) geometry.dispose(); // sprites share one geometry
    for (const m of Array.isArray(material) ? material : material ? [material] : []) m.dispose();
  });
  root.clear();
}

/** Update moving points in place: grow the buffer only when it's too small, and draw just the points given. */
export function setPositions(geometry: THREE.BufferGeometry, values: number[]): void {
  let buffer = geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
  if (!buffer || buffer.array.length < values.length) {
    geometry.dispose(); // the old buffer's GPU copy
    buffer = new THREE.BufferAttribute(new Float32Array(Math.max(values.length, 3) * 2), 3);
    buffer.setUsage(THREE.DynamicDrawUsage);
    geometry.setAttribute("position", buffer);
  }
  (buffer.array as Float32Array).set(values);
  buffer.needsUpdate = true;
  geometry.setDrawRange(0, values.length / 3);
}
