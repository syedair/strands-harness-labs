import { describe, expect, it } from "vitest";
import { applyEvent, newAssistantTurn } from "./chat";

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
