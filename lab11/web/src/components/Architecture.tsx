// "How it works": one turn through the app, a click at a time. Parts appear the first time a step uses them.
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { BOX, HARNESS, NODES, STEPS, VIEW, labelSpot, linkEnds, sceneAt, type Step, type Tone } from "../architecture";

const TONE: Record<Tone, string> = { plain: "#F8FAFC", s1: "#6EE7B7", llm: "#22D3EE", save: "#A78BFA" };
const byId = new Map(NODES.map((n) => [n.id, n]));

function Link({ step, live }: { step: Step; live: boolean }) {
  const { x1, y1, x2, y2 } = linkEnds(byId.get(step.from)!, byId.get(step.to)!);
  const color = live ? TONE[step.tone] : "rgba(248,250,252,0.22)";
  const path = `M${x1} ${y1} L${x2} ${y2}`;
  const width = step.label.length * 7.2 + 20;
  const spot = labelSpot({ x1, y1, x2, y2 }, width, 22);
  return (
    <g>
      <path d={path} stroke={color} strokeWidth={live ? 2.5 : 1.5} fill="none" markerEnd={`url(#arrow-${live ? step.tone : "past"})`}
            markerStart={step.back ? `url(#arrow-${live ? step.tone : "past"})` : undefined}
            strokeDasharray={live ? undefined : "4 5"} />
      {live && (
        <>
          <circle r="5" fill={color}>
            {step.back /* a round trip: out to the part and back to the Agent */
              ? <animateMotion dur="1.8s" repeatCount="indefinite" path={path} keyPoints="0;1;0" keyTimes="0;0.5;1" calcMode="linear" />
              : <animateMotion dur="1.1s" repeatCount="indefinite" path={path} />}
          </circle>
          <g transform={`translate(${spot.x} ${spot.y})`}>
            <rect x={-width / 2} y="-11" width={width} height="22" rx="11" fill="#0B1120" stroke={color} strokeOpacity="0.6" />
            <text textAnchor="middle" dy="4" fill={color} fontSize="11" fontFamily="var(--font-mono)">{step.label}</text>
          </g>
        </>
      )}
    </g>
  );
}

export function Architecture() {
  const [at, setAt] = useState(-1);
  const scene = sceneAt(at);
  const last = STEPS.length - 1;
  const active = new Set(scene.current ? [scene.current.from, scene.current.to] : ["browser"]);
  const harnessShown = NODES.some((n) => n.inHarness && scene.shown.has(n.id));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); setAt((i) => Math.min(i + 1, last)); }
      if (e.key === "ArrowLeft") setAt((i) => Math.max(i - 1, -1));
      if (e.key === "Home") setAt(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [last]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 overflow-y-auto">
      <p className="text-sm text-ink-2">One turn through the app. Click <b className="text-ink">Next</b> or press → to follow a message.</p>

      <div className="glass overflow-x-auto rounded-2xl bg-black/25 p-3">
        <svg viewBox={`0 0 ${VIEW.width} ${VIEW.height}`} className="h-[min(56vh,540px)] w-full min-w-[720px]" role="img"
             aria-label={scene.current ? scene.current.title : "The app, before a message is sent"}>
          <defs>
            {(["plain", "s1", "llm", "save"] as Tone[]).map((t) => (
              <marker key={t} id={`arrow-${t}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                <path d="M0 0L10 5L0 10z" fill={TONE[t]} />
              </marker>
            ))}
            <marker id="arrow-past" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
              <path d="M0 0L10 5L0 10z" fill="rgba(248,250,252,0.3)" />
            </marker>
          </defs>

          <g style={{ opacity: harnessShown ? 1 : 0, transition: "opacity 500ms" }}>
            <rect x={HARNESS.x} y={HARNESS.y} width={HARNESS.width} height={HARNESS.height} rx="22"
                  fill="rgba(34,211,238,0.035)" stroke="rgba(34,211,238,0.35)" strokeDasharray="6 6" />
            <text x={HARNESS.x + 18} y={HARNESS.y + 26} fill="#22D3EE" fontSize="11" letterSpacing="2.4" fontFamily="var(--font-mono)">
              STRANDS HARNESS
            </text>
          </g>

          {scene.past.map((s, i) => <Link key={`past-${i}`} step={s} live={false} />)}

          {NODES.map((n) => {
            const shown = scene.shown.has(n.id);
            const on = active.has(n.id);
            const tone = scene.current && on ? (n.tone === "plain" ? scene.current.tone : n.tone) : n.tone;
            const edge = on ? TONE[tone] : n.tone === "plain" ? "rgba(248,250,252,0.16)" : `${TONE[n.tone]}66`;
            return (
              <g key={n.id} transform={`translate(${n.x} ${n.y})`}
                 style={{ opacity: shown ? 1 : 0, transition: "opacity 450ms ease" }}>
                {on && <rect x={-BOX.width / 2 - 8} y={-BOX.height / 2 - 8} width={BOX.width + 16} height={BOX.height + 16} rx="18"
                             fill={TONE[tone]} opacity="0.10" />}
                <rect x={-BOX.width / 2} y={-BOX.height / 2} width={BOX.width} height={BOX.height} rx="13"
                      fill="#111D31" stroke={edge} strokeWidth={on ? 2 : 1.2} />
                <text textAnchor="middle" y="-3" fill={n.tone === "plain" ? "#F8FAFC" : TONE[n.tone]} fontSize="15" fontWeight="600">{n.label}</text>
                <text textAnchor="middle" y="16" fill="rgba(248,250,252,0.6)" fontSize="10.5" fontFamily="var(--font-mono)">{n.detail}</text>
              </g>
            );
          })}

          {scene.current && <Link key={`live-${at}`} step={scene.current} live />}
        </svg>
      </div>

      <div className="glass grid gap-4 rounded-2xl p-5 md:grid-cols-[1fr_auto] md:items-end">
        <div key={at} className="animate-rise min-w-0 space-y-2">
          <p className="eyebrow text-[0.65rem]" style={{ color: scene.current ? TONE[scene.current.tone] : undefined }}>
            {scene.current ? `Step ${at + 1} of ${STEPS.length}` : "Ready"}
          </p>
          <h2 className="font-display text-xl font-semibold">{scene.current ? scene.current.title : "A message is about to be sent"}</h2>
          <p className="max-w-[65ch] text-ink-2">
            {scene.current ? scene.current.text : "System 1 checks the LLM's work at three points: which memories to use, which tool calls to allow, and whether the answer is complete."}
          </p>
          {scene.current?.example && (
            <p className="max-w-[80ch] rounded-lg bg-black/30 px-3 py-2 font-mono text-xs text-ink">
              <span className="mr-2 text-ink-2">for example</span>{scene.current.example}
            </p>
          )}
        </div>
        <div className="flex flex-col items-start gap-3 md:items-end">
          <div className="flex gap-1.5" aria-label="Steps">
            {STEPS.map((s, i) => (
              <button key={i} onClick={() => setAt(i)} aria-label={`Step ${i + 1}: ${s.title}`}
                      className={`press h-2 rounded-full transition-all ${i === at ? "w-6" : "w-2"} ${i <= at ? "" : "bg-white/15"}`}
                      style={i <= at ? { background: TONE[s.tone] } : undefined} />
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setAt(-1)} disabled={at < 0} aria-label="Start over"
                    className="press rounded-full border border-white/15 p-2 text-ink-2 hover:text-ink disabled:opacity-40">
              <RotateCcw size={16} />
            </button>
            <button onClick={() => setAt((i) => Math.max(i - 1, -1))} disabled={at < 0}
                    className="press flex items-center gap-1 rounded-full border border-white/15 px-3 py-2 text-sm text-ink-2 hover:text-ink disabled:opacity-40">
              <ChevronLeft size={16} /> Back
            </button>
            <button onClick={() => setAt((i) => Math.min(i + 1, last))} disabled={at === last}
                    className="press flex items-center gap-1 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-bg-1 hover:brightness-110 disabled:opacity-40">
              {at < 0 ? "Start" : "Next"} <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
