# Lab 7: System 1 gate — check a tool call before it runs; block guessed arguments.
import json

from strands.interventions import Deny, Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama
from common.show import checklist, wait
from common.system1 import check_system1, display_name, yes_no_many

# An "eager" assistant that guesses instead of asking — the failure we want to catch.
INSTRUCTIONS = (
    "You are an eager travel assistant. For weather, immediately fetch "
    "https://wttr.in/<city>?format=3 with web_fetch. If no city is given, assume Seattle."
)

# What we ask System 1 about every tool call. Four narrow yes/no questions, answered in one fast call.
QUESTIONS = {
    # Concrete beats abstract: "a sensible step towards answering?" scored 0.21-0.43 on Kev for packing requests.
    "matches_intent": "Would the result of this tool call help answer what the user asked, even partly? "
                      "For example, a weather forecast helps decide what to pack.",
    "missing_info": "Is information missing that the tool needs to run correctly?",
    # Small open models need concrete questions: "grounded?" is too abstract for a 4B model.
    "args_grounded": "Did the user mention the same city that the tool call uses?",
    "premature": "Is it too early to call this tool, before clarifying with the user?",
}
# How each question reads on screen, and whether a YES is what we want.
LABELS = {"matches_intent": ("helps answer?", True), "missing_info": ("information missing?", False),
          "args_grounded": ("same city as the user?", True), "premature": ("too early?", False)}


def user_text(messages: list[dict]) -> str:
    # Only what the USER said: the model's own "I'll assume Seattle" must not count as grounding.
    lines = [f"user: {block['text']}" for m in messages if m["role"] == "user" for block in m["content"] if "text" in block]
    return "\n".join(lines)


class ToolCallGate(InterventionHandler):
    """An intervention: the harness calls before_tool_call every time the model wants to run a tool,
    and the tool only runs if we return Proceed."""

    name = "system1-tool-call-gate"
    YES = 0.65  # the policy knob: what counts as a confident "yes"
    MAX_BLOCKS = 3  # Guide lets the model try again, so cap it
    PAUSE = True  # wait for Enter before asking System 1 (only in a terminal)

    def __init__(self):
        self.blocks = 0

    def before_tool_call(self, event):
        # 1. What the model wants to do, and what the user actually said.
        call = f"{event.tool_use['name']}({json.dumps(event.tool_use.get('input', {}))})"
        state = f"{self.context(event)}\n\nProposed tool call: {call}"
        print(f"\n  gate · the model wants to run: {call}")
        if self.PAUSE:
            wait(f"press Enter to ask {display_name()}")

        # 2. Ask System 1 the four questions. It only gives probabilities: it never decides.
        p = yes_no_many(state, QUESTIONS)  # System 1 observes...
        self.last_probs = p  # lab 11 shows these in the web UI
        checklist([(label, p[name], p[name] >= self.YES if want_yes else p[name] < self.YES)
                   for name, (label, want_yes) in LABELS.items()], threshold=self.YES)

        # 3. ...plain Python decides. Any broken rule blocks the call; the first one that fails explains why.
        if p["matches_intent"] < self.YES:  # the tool wouldn't help with this request
            return self.block("the tool doesn't match the request", "Blocked: that tool doesn't fit the request, so it didn't run. Don't report any results from it. Reconsider which tool, if any, fits.")
        if p["missing_info"] >= self.YES or p["args_grounded"] < self.YES:  # the city is a guess
            return self.block("ask the user instead of guessing",
                              "Blocked: the city is a guess, so the tool didn't run and you have no data. "
                              "Don't report any weather. Ask the user which city they mean.")
        if p["premature"] >= self.YES:  # it should ask the user something first
            return self.block("too early, clarify first", "Blocked: it's too early, so the tool didn't run. Don't report any results. Clarify with the user first.")
        print("  gate → Proceed: the tool runs")
        return Proceed()

    def context(self, event) -> str:
        """What the classifier sees besides the tool call: here, only what the user said."""
        return user_text(event.agent.messages)

    def block(self, why: str, feedback: str):
        """Guide: the tool doesn't run, and the model reads our feedback and tries again.
        Deny: after MAX_BLOCKS guides, stop the call for good, so a stubborn model can't loop forever."""
        self.last_why = why  # lab 11 shows which rule fired
        self.blocks += 1
        if self.blocks > self.MAX_BLOCKS:
            print(f"  gate → Deny: {why} (blocked {self.MAX_BLOCKS}x already)")
            return Deny(reason=feedback)
        print(f"  gate → Guide ({self.blocks}/{self.MAX_BLOCKS}): {why}")
        return Guide(feedback=feedback, reason=why)


def main() -> None:
    check_ollama(MAIN_MODEL)
    check_system1()
    print(f"System 1: {display_name()}")  # set SYSTEM1_MODEL in .env to switch
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=False,
        interventions=ToolCallGate(),  # NEW: our own System 1 gate
    )
    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    for question in ["What's the weather?",  # no city: the model guesses, the gate blocks it
                     "What's the weather in Paris?"]:  # a real city: the gate lets it through
        print(f"\nyou: {question}")
        agent(question)
        agent.messages.clear()


if __name__ == "__main__":
    main()
