# Lab 8: System 1 completion check — send the agent back when it stops before the job is done.
from strands.interventions import Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama
from common.show import checklist, wait
from common.system1 import check_system1, yes_no

# A "lazy" assistant that answers only the first part of a request.
INSTRUCTIONS = (
    "You are a travel assistant. For weather, fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "Answer only the first thing the user asks and then stop."
)


def text_of(message: dict) -> str:
    return "\n".join(block["text"] for block in message["content"] if "text" in block)


class CompletionCheck(InterventionHandler):
    name = "system1-completion-check"
    MAX_GUIDES = 2  # Guide retries the model, so we must cap it
    PASS = 0.6  # the policy knob: how sure System 1 must be that every part was answered
    PAUSE = True  # wait for Enter before asking System 1 (only in a terminal)

    def __init__(self):
        self.guides = 0  # one agent call per run, so never reset

    def after_model_call(self, event):
        response = event.stop_response
        if response is None or response.stop_reason != "end_turn":
            return Proceed()  # only judge final answers, not tool-use turns

        request = text_of(event.agent.messages[0])
        answer = text_of(response.message)
        if answer.rstrip().endswith("?"):  # asking the user something back is a fine way to end a turn
            print("\n  check → Proceed: it asked you a question, nothing to judge")
            return Proceed()
        short = " ".join(answer.split())
        print(f"\n  check · the model's answer: “{short[:90]}{'…' if len(short) > 90 else ''}”")
        if self.PAUSE:
            wait("press Enter to ask System 1")
        p_complete = yes_no(  # System 1 observes...
            f"User request: {request}\n\nAssistant answer: {answer}",
            "Does the assistant's answer respond to every question the user asked?",
        )
        self.last_probs = {"answered_everything": p_complete}  # lab 11 shows this in the web UI
        checklist([("answered everything?", p_complete, p_complete >= self.PASS)], threshold=self.PASS)

        # ...plain Python decides.
        if p_complete >= self.PASS or self.guides >= self.MAX_GUIDES:
            print("  check → Proceed: the answer goes to the user")
            return Proceed()
        self.guides += 1
        print(f"  check → Guide ({self.guides}/{self.MAX_GUIDES}): finish the rest of the request")
        return Guide(feedback="Your answer skipped part of the request. Answer every part the user asked for.")


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
        interventions=CompletionCheck(),  # NEW
    )
    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    question = "What's the weather in Istanbul, and what should I pack for 4 days there?"
    print(f"\nyou: {question}")
    agent(question)


if __name__ == "__main__":
    main()
