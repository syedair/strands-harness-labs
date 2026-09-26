// The memory core: a nebula of particles with each real memory note as a bright anchor star.
// Recalled notes flare and pulses travel out to them from the core; it spins faster while the agent works.
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { MemoryGraph } from "../api";
import { cloudPoints, spherePoint } from "../globe";

const CYAN = new THREE.Color("#22D3EE");
const ACCENT = new THREE.Color("#6EE7B7");
const VIOLET = new THREE.Color("#A78BFA"); // a memory being stored
const PRIMED = CYAN.clone().lerp(ACCENT, 0.5); // a neighbour the activation spread to
const RADIUS = 60;
const PARTICLES = 2600;
const SPEED = { idle: 0.0015, thinking: 0.004, working: 0.006, writing: 0.003 } as const;
export type CoreState = keyof typeof SPEED;

function glowTexture(): THREE.Texture {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const g = canvas.getContext("2d")!;
  const dot = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  dot.addColorStop(0, "rgba(255,255,255,1)");
  dot.addColorStop(0.25, "rgba(255,255,255,0.55)");
  dot.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = dot;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

const glowing = (color: THREE.Color, opacity: number, map: THREE.Texture) =>
  ({ color, opacity, map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });

type Props = { graph: MemoryGraph; fired: string[]; stored: string[]; state: CoreState; height: number; close?: boolean };

export function MemoryCore({ graph, fired, stored, state, height, close = false }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const live = useRef({ fired: new Set<string>(), stored: new Set<string>(), state, rebuild: (_g: MemoryGraph) => {} });
  const [hover, setHover] = useState<{ text: string; x: number; y: number } | null>(null);
  live.current.state = state;
  live.current.fired = new Set(fired);
  live.current.stored = new Set(stored);

  useEffect(() => {
    const el = box.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 1, 2000);
    camera.position.set(0, 0, RADIUS * (close ? 2.5 : 3.2)); // closer in the full-screen view
    camera.lookAt(0, 0, 0);
    const texture = glowTexture();
    const core = new THREE.Group();
    scene.add(core);

    // the nebula: particles plus thin lines between close neighbours
    const points = cloudPoints(PARTICLES, RADIUS);
    const cloud = new THREE.BufferGeometry().setFromPoints(points.map((p) => new THREE.Vector3(p.x, p.y, p.z)));
    const cloudMaterial = new THREE.PointsMaterial({ size: 2.6, ...glowing(CYAN, 0.7, texture) });
    core.add(new THREE.Points(cloud, cloudMaterial));
    const near: number[] = [];
    for (let i = 0; i < points.length; i += 3) {
      for (let j = i + 1; j < Math.min(points.length, i + 40); j++) {
        const a = points[i], b = points[j];
        if (Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) < 13) near.push(a.x, a.y, a.z, b.x, b.y, b.z);
      }
    }
    const web = new THREE.BufferGeometry();
    web.setAttribute("position", new THREE.Float32BufferAttribute(near, 3));
    core.add(new THREE.LineSegments(web, new THREE.LineBasicMaterial({ ...glowing(CYAN, 0.14, texture), map: null })));
    const glow = new THREE.Sprite(new THREE.SpriteMaterial(glowing(CYAN, 0.35, texture)));
    glow.scale.setScalar(RADIUS * 1.6);
    core.add(glow);

    // the memory notes: anchor stars, links between related notes, and pulses from the core when recalled
    const anchors = new THREE.Group();
    core.add(anchors);
    let stars: { id: string; text: string; sprite: THREE.Sprite; pos: THREE.Vector3 }[] = [];
    let links: { a: string; b: string; strength: number; line: THREE.Line }[] = [];
    const pulses = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ size: 3.5, ...glowing(ACCENT, 1, texture) }));
    core.add(pulses);
    const gathering = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ size: 3.5, ...glowing(VIOLET, 1, texture) }));
    core.add(gathering);
    live.current.rebuild = (g: MemoryGraph) => {
      anchors.clear();
      stars = g.nodes.map((n, i) => {
        const p = spherePoint(i, g.nodes.length, RADIUS * 0.72);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial(glowing(CYAN, 1, texture)));
        sprite.position.set(p.x, p.y, p.z);
        sprite.scale.setScalar(7 + Math.log2(1 + n.hits) * 2);
        anchors.add(sprite);
        return { id: n.id, text: n.text, sprite, pos: sprite.position.clone() };
      });
      const at = new Map(stars.map((s) => [s.id, s.pos]));
      links = g.links.filter((l) => at.has(l.source) && at.has(l.target)).map((l) => {
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([at.get(l.source)!, at.get(l.target)!]),
          new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending }));
        anchors.add(line);
        return { a: l.source, b: l.target, strength: l.weight + Math.log2(1 + l.together), line };
      });
    };

    const resize = () => {
      const width = el.clientWidth;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    resize();

    const raycaster = new THREE.Raycaster();
    const onMove = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      raycaster.setFromCamera(mouse, camera);
      const hit = raycaster.intersectObjects(stars.map((s) => s.sprite))[0];
      const star = hit && stars.find((s) => s.sprite === hit.object);
      setHover(star ? { text: star.text, x: e.clientX - rect.left, y: e.clientY - rect.top } : null);
    };
    renderer.domElement.addEventListener("pointermove", onMove);

    let frame = 0;
    const animate = (time: number) => {
      const { fired: hot, stored: fresh, state: now } = live.current;
      const busy = now !== "idle";
      core.rotation.y += SPEED[now];
      cloudMaterial.opacity = busy ? 0.95 : 0.7;
      glow.material.opacity = (busy ? 0.5 : 0.3) + 0.05 * Math.sin(time / 600);
      const flare = 1 + 0.4 * Math.sin(time / 160);
      // spreading activation: recalled notes fire, their direct neighbours are primed (one hop)
      const primed = new Set<string>();
      for (const l of links) {
        if (hot.has(l.a) && !hot.has(l.b)) primed.add(l.b);
        if (hot.has(l.b) && !hot.has(l.a)) primed.add(l.a);
      }
      for (const s of stars) {
        const on = hot.has(s.id);
        const saving = fresh.has(s.id);
        const warm = primed.has(s.id);
        s.sprite.material.color = saving ? VIOLET : on ? ACCENT : warm ? PRIMED : CYAN;
        s.sprite.material.opacity = on || saving ? 1 : warm ? 0.95 : 0.8;
        s.sprite.scale.setScalar(on || saving ? 12 * flare : warm ? 9 + Math.sin(time / 300) : 7);
      }
      // links: co-firing (both ends recalled) is brightest; spreading (one end) is dimmer; idle shows
      // how strongly the two are wired (similar meaning + how often they were recalled together)
      const spread: number[] = [];
      for (const l of links) {
        const ends = Number(hot.has(l.a)) + Number(hot.has(l.b));
        const material = l.line.material as THREE.LineBasicMaterial;
        material.color = ends > 0 ? ACCENT : CYAN;
        material.opacity = ends === 2 ? 0.95 : ends === 1 ? 0.55 : 0.1 + Math.min(l.strength, 3) * 0.08;
        if (ends === 0) continue;
        const [from, to] = hot.has(l.a) ? [l.a, l.b] : [l.b, l.a];
        const start = stars.find((s) => s.id === from)!.pos, end = stars.find((s) => s.id === to)!.pos;
        for (let i = 0; i < 4; i++) {
          const t = (time / 900 + i / 4) % 1;
          const forward = ends === 1 || i % 2 === 0; // co-firing runs both ways
          spread.push(...start.clone().lerp(end, forward ? t : 1 - t).toArray());
        }
      }
      // storing: violet points gather from outside the core into each new note (recall fires the other way)
      const incoming: number[] = [];
      stars.filter((s) => fresh.has(s.id)).forEach((s) => {
        const outside = s.pos.clone().normalize().multiplyScalar(RADIUS * 1.6);
        for (let i = 0; i < 16; i++) {
          const spread = new THREE.Vector3(Math.sin(i * 2.4), Math.cos(i * 1.7), Math.sin(i * 0.9)).multiplyScalar(RADIUS * 0.5);
          const t = (time / 1600 + i / 16) % 1;
          const from = outside.clone().add(spread);
          incoming.push(...from.lerp(s.pos, t).toArray());
        }
      });
      gathering.geometry.setAttribute("position", new THREE.Float32BufferAttribute(incoming, 3));
      // pulses: points travelling from the core out to each recalled note, over and over
      const targets = stars.filter((s) => hot.has(s.id));
      const trail: number[] = [...spread];
      targets.forEach((s, k) => {
        for (let i = 0; i < 6; i++) {
          const t = ((time / 1400 + i / 6 + k * 0.13) % 1);
          trail.push(s.pos.x * t, s.pos.y * t, s.pos.z * t);
        }
      });
      pulses.geometry.setAttribute("position", new THREE.Float32BufferAttribute(trail, 3));
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointermove", onMove);
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [height, close]);

  useEffect(() => live.current.rebuild(graph), [graph, height, close]);

  return (
    <div ref={box} className="relative w-full" style={{ height }}>
      {hover && (
        <p className="glass pointer-events-none absolute z-10 max-w-60 rounded-lg px-2 py-1 text-xs"
           style={{ left: hover.x + 12, top: hover.y + 12 }}>{hover.text}</p>
      )}
    </div>
  );
}
