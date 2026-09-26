# Lab 7: System 1 gate — check a tool call before it runs; block guessed arguments.
import json

from strands.interventions import Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.config import MAIN_MODEL, SYSTEM1_MODEL, check_ollama
from common.system1 import yes_no_many

# An "eager" assistant that guesses instead of asking — the failure we want to catch.
INSTRUCTIONS = (
    "You are an eager travel assistant. For weather, immediately fetch "
    "https://wttr.in/<city>?format=3 with web_fetch. Never ask for clarification: "
    "if no city is given, assume Seattle."
)

QUESTIONS = {
    "matches_intent": "Does the proposed tool match what the user is asking for?",
    "missing_info": "Is information missing that the tool needs to run correctly?",
    # Small open models need concrete questions: "grounded?" is too abstract for a 4B model.
    "args_grounded": "Did the user mention the same city that the tool call uses?",
    "premature": "Is it too early to call this tool, before clarifying with the user?",
}


def conversation_text(messages: list[dict]) -> str:
    lines = [f"{m['role']}: {block['text']}" for m in messages for block in m["content"] if "text" in block]
    return "\n".join(lines)


class ToolCallGate(InterventionHandler):
    name = "system1-tool-call-gate"
    YES = 0.65  # the policy knob: what counts as a confident "yes"

    def before_tool_call(self, event):
        call = f"{event.tool_use['name']}({json.dumps(event.tool_use.get('input', {}))})"
        state = f"{conversation_text(event.agent.messages)}\n\nProposed tool call: {call}"
        print(f"\n[gate] model proposes: {call}")

        p = yes_no_many(state, QUESTIONS)  # System 1 observes...
        for name, value in p.items():
            print(f"[gate]   P({name}) = {value:.2f}")

        # ...plain Python decides.
        if p["matches_intent"] < self.YES:
            return Guide(feedback="That tool doesn't match the request. Reconsider.")
        if p["missing_info"] >= self.YES or p["args_grounded"] < self.YES:
            print("[gate] -> Guide: ask the user instead of guessing")
            return Guide(feedback="Blocked: the arguments are guessed, not from the user. Do not call any tool. Reply by asking the user for the missing details.")
        if p["premature"] >= self.YES:
            return Guide(feedback="Too early to call this tool. Clarify with the user first.")
        print("[gate] -> Proceed")
        return Proceed()


def main() -> None:
    check_ollama(MAIN_MODEL, SYSTEM1_MODEL)
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
