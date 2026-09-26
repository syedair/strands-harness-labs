# Lab 7: System 1 gate — check a tool call before it runs; block guessed arguments.
import json

from strands.interventions import Deny, Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama
from common.system1 import check_system1, yes_no_many

# An "eager" assistant that guesses instead of asking — the failure we want to catch.
INSTRUCTIONS = (
    "You are an eager travel assistant. For weather, immediately fetch "
    "https://wttr.in/<city>?format=3 with web_fetch. If no city is given, assume Seattle."
)

QUESTIONS = {
    "matches_intent": "Could this tool call help with what the user asked for?",
    "missing_info": "Is information missing that the tool needs to run correctly?",
    # Small open models need concrete questions: "grounded?" is too abstract for a 4B model.
    "args_grounded": "Did the user mention the same city that the tool call uses?",
    "premature": "Is it too early to call this tool, before clarifying with the user?",
}


def user_text(messages: list[dict]) -> str:
    # Only what the USER said: the model's own "I'll assume Seattle" must not count as grounding.
    lines = [f"user: {block['text']}" for m in messages if m["role"] == "user" for block in m["content"] if "text" in block]
    return "\n".join(lines)


class ToolCallGate(InterventionHandler):
    name = "system1-tool-call-gate"
    YES = 0.65  # the policy knob: what counts as a confident "yes"
    MAX_BLOCKS = 3  # Guide lets the model try again, so cap it

    def __init__(self):
        self.blocks = 0

    def before_tool_call(self, event):
        call = f"{event.tool_use['name']}({json.dumps(event.tool_use.get('input', {}))})"
        state = f"{self.context(event)}\n\nProposed tool call: {call}"
        print(f"\n[gate] model proposes: {call}")

        p = yes_no_many(state, QUESTIONS)  # System 1 observes...
        self.last_probs = p  # lab 11 shows these in the web UI
        for name, value in p.items():
            print(f"[gate]   P({name}) = {value:.2f}")

        # ...plain Python decides.
        if p["matches_intent"] < self.YES:
            return self.block("the tool doesn't match the request", "That tool doesn't match the request. Reconsider.")
        if p["missing_info"] >= self.YES or p["args_grounded"] < self.YES:
            return self.block("ask the user instead of guessing",
                              "Blocked: the city is a guess, so nothing was fetched and you have no weather data. "
                              "Do not report any weather. Ask the user which city they mean.")
        if p["premature"] >= self.YES:
            return self.block("too early, clarify first", "Too early to call this tool. Clarify with the user first.")
        print("[gate] -> Proceed")
        return Proceed()

    def context(self, event) -> str:
        """What the classifier sees besides the tool call: here, only what the user said."""
        return user_text(event.agent.messages)

    def block(self, why: str, feedback: str):
        self.last_why = why  # lab 11 shows which rule fired
        self.blocks += 1
        if self.blocks > self.MAX_BLOCKS:
            print(f"[gate] -> Deny: {why} (blocked {self.MAX_BLOCKS}x already)")
            return Deny(reason=feedback)
        print(f"[gate] -> Guide ({self.blocks}/{self.MAX_BLOCKS}): {why}")
        return Guide(feedback=feedback, reason=why)


def main() -> None:
    check_ollama(MAIN_MODEL)
    check_system1()
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=False,
        interventions=ToolCallGate(),  # NEW: our own System 1 gate
    )
    agent("What's the weather?")  # no city: the model guesses, the gate blocks it
    agent.messages.clear()
    agent("What's the weather in Paris?")  # a real city: the gate lets it through


if __name__ == "__main__":
    main()
