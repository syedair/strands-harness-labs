import { describe, expect, it } from "vitest";
import { applyEvent, finishTurn, newAssistantTurn, splitTurn, statusOf, turnsFromHistory } from "./chat";

describe("applyEvent", () => {
  it("appends streamed text into one part", () => {
    let turn = newAssistantTurn();
    turn = applyEvent(turn, { type: "text", delta: "Hello " });
    turn = applyEvent(turn, { type: "text", delta: "there" });
    expect(turn.parts).toEqual([{ kind: "text", text: "Hello there", discarded: false }]);
  });

  it("marks the streamed draft as sent back when the check guides", () => {
    let turn = newAssistantTurn();
    turn = applyEvent(turn, { type: "text", delta: "It's 21°C." });
    turn = applyEvent(turn, { type: "decision", source: "check", action: "guide", why: null, p: 0.16, probs: { answered_everything: 0.16 } });
    turn = applyEvent(turn, { type: "text", delta: "It's 21°C. Pack a jacket." });
    expect(turn.parts[0]).toEqual({ kind: "text", text: "It's 21°C.", discarded: true });
    expect(turn.parts[1].kind).toBe("decision");
    expect(turn.parts[2]).toEqual({ kind: "text", text: "It's 21°C. Pack a jacket.", discarded: false });
  });

  it("keeps text before and after a gate decision as separate parts", () => {
    let turn = newAssistantTurn();
    turn = applyEvent(turn, { type: "text", delta: "Checking." });
    turn = applyEvent(turn, { type: "tool", name: "web_fetch", input: { url: "https://wttr.in/Seattle" } });
    turn = applyEvent(turn, { type: "decision", source: "gate", action: "guide", why: "ask the user instead of guessing", p: 0.34, probs: { args_grounded: 0.34 } });
    turn = applyEvent(turn, { type: "text", delta: "Which city?" });
    expect(turn.parts.map((p) => p.kind)).toEqual(["text", "tool", "decision", "text"]);
    expect(turn.parts[0]).toMatchObject({ discarded: false });
    expect(turn.parts[2]).toMatchObject({ why: "ask the user instead of guessing", p: 0.34 });
  });

  it("stops streaming on done and on error", () => {
    expect(applyEvent(newAssistantTurn(), { type: "done" }).streaming).toBe(false);
    const failed = applyEvent(newAssistantTurn(), { type: "error", message: "Bedrock throttled" });
    expect(failed).toMatchObject({ streaming: false, error: "Bedrock throttled" });
  });
});

describe("statusOf", () => {
  it("is thinking before anything arrives", () => {
    expect(statusOf(newAssistantTurn())).toBe("thinking");
  });

  it("is working while a tool runs: after the call, and after the gate allows it", () => {
    let turn = applyEvent(newAssistantTurn(), { type: "tool", name: "web_fetch", input: {} });
    expect(statusOf(turn)).toBe("working");
    turn = applyEvent(turn, { type: "decision", source: "gate", action: "proceed", why: null, p: 0.9, probs: {} });
    expect(statusOf(turn)).toBe("working");
    turn = applyEvent(turn, { type: "decision", source: "check", action: "proceed", why: null, p: 0.9, probs: {} });
    expect(statusOf(turn)).toBe("thinking");
  });

  it("is writing while text streams, and done at the end", () => {
    const writing = applyEvent(newAssistantTurn(), { type: "text", delta: "Hi" });
    expect(statusOf(writing)).toBe("writing");
    expect(statusOf(applyEvent(writing, { type: "done" }))).toBe("done");
  });
});

describe("memory, history and early endings", () => {
  it("shows recalled memories as a part of the reply", () => {
    const turn = applyEvent(newAssistantTurn(), { type: "memory", ids: ["home.md", "trip.md"], scores: [0.9, 0.7], query: "home?" });
    expect(turn.parts[0]).toMatchObject({ kind: "memory", ids: ["home.md", "trip.md"] });
  });

  it("turns saved history into finished turns", () => {
    expect(turnsFromHistory([{ role: "user", text: "hi" }, { role: "assistant", text: "Hello!" }])).toEqual([
      { role: "user", text: "hi" },
      { role: "assistant", parts: [{ kind: "text", text: "Hello!", discarded: false }], streaming: false },
    ]);
  });

  it("ends a reply that stopped without done or error", () => {
    const cut = finishTurn(applyEvent(newAssistantTurn(), { type: "text", delta: "Half" }));
    expect(cut).toMatchObject({ streaming: false, error: "The reply ended early." });
    const done = applyEvent(newAssistantTurn(), { type: "done" });
    expect(finishTurn(done)).toBe(done);
  });
});

describe("recall details and saved memories", () => {
  it("keeps what was searched and how relevant each memory was", () => {
    const turn = applyEvent(newAssistantTurn(), { type: "memory", ids: ["name.md"], scores: [0.95], query: "What's my name?" });
    expect(turn.parts).toEqual([{ kind: "memory", ids: ["name.md"], scores: [0.95], query: "What's my name?" }]);
  });

  it("shows a saved memory as its own part", () => {
    const turn = applyEvent(newAssistantTurn(), { type: "stored", ids: ["airline.md"] });
    expect(turn.parts).toEqual([{ kind: "stored", ids: ["airline.md"] }]);
  });
});

describe("splitTurn", () => {
  const ev = (e: Parameters<typeof applyEvent>[1]) => e;
  const turnOf = (...events: Parameters<typeof applyEvent>[1][]) => events.reduce(applyEvent, newAssistantTurn());

  it("keeps only the last answer up front; everything before it is a step", () => {
    const turn = turnOf(
      ev({ type: "memory", ids: ["a.md", "b.md"], scores: [0.9, 0.7], query: "who am I" }),
      ev({ type: "text", delta: "You're Syed, though…" }),
      ev({ type: "decision", source: "check", action: "guide", why: null, p: 0.28, probs: {} }),
      ev({ type: "tool", name: "search_memory", input: {} }),
      ev({ type: "text", delta: "You're John." }),
      ev({ type: "decision", source: "check", action: "proceed", why: null, p: 0.8, probs: {} }),
      ev({ type: "stored", ids: ["c.md"] }),
      ev({ type: "done" }),
    );
    const { answer, steps, summary } = splitTurn(turn);
    expect(answer).toEqual({ kind: "text", text: "You're John.", discarded: false });
    expect(steps.map((p) => p.kind)).toEqual(["memory", "text", "decision", "tool", "decision", "stored"]);
    expect(summary).toEqual({ recalled: 2, tools: 1, blocked: 0, allowed: 0, sentBack: 1, saved: 1, forgot: 0 });
  });

  it("counts memories the agent forgot", () => {
    const turn = turnOf(ev({ type: "forgot", ids: ["name.md", "name-2.md"] }), ev({ type: "text", delta: "Done." }));
    expect(turn.parts[0]).toEqual({ kind: "forgot", ids: ["name.md", "name-2.md"] });
    expect(splitTurn(turn).summary.forgot).toBe(2);
  });

  it("counts the gate's decisions", () => {
    const turn = turnOf(
      ev({ type: "tool", name: "web_fetch", input: {} }),
      ev({ type: "decision", source: "gate", action: "guide", why: "ask the user instead of guessing", p: 0.3, probs: {} }),
      ev({ type: "tool", name: "web_fetch", input: {} }),
      ev({ type: "decision", source: "gate", action: "proceed", why: null, p: 0.9, probs: {} }),
      ev({ type: "text", delta: "Sunny." }),
    );
    expect(splitTurn(turn).summary).toMatchObject({ tools: 2, blocked: 1, allowed: 1 });
  });

  it("has no answer until text arrives", () => {
    expect(splitTurn(turnOf(ev({ type: "tool", name: "web_fetch", input: {} }))).answer).toBeNull();
  });
});

describe("reasoning a model streams as text", () => {
  it("moves everything before </think> into the steps, even when the tag is split across deltas", () => {
    const turn = [
      { type: "text", delta: "I can see the user wants AWS docs.</thi" },
      { type: "text", delta: "nk> Yes! I now have" },
      { type: "text", delta: " access." },
    ].reduce((t, e) => applyEvent(t, e as Parameters<typeof applyEvent>[1]), newAssistantTurn());
    const { answer, steps } = splitTurn(turn);
    expect(answer?.text).toBe("Yes! I now have access.");
    expect(steps).toEqual([{ kind: "text", text: "I can see the user wants AWS docs.", discarded: false }]);
  });
});
