# Lab 8: System 1 completion check — send the agent back when it stops before the job is done.
from strands.interventions import Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama
from common.show import checklist, wait
from common.system1 import check_system1, display_name, yes_no_many

# A "lazy" assistant that answers only the first part of a request.
INSTRUCTIONS = (
    "You are a travel assistant. For weather, fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "Answer only the first thing the user asks and then stop."
)


FEEDBACK = "Your answer skipped part of the request. Answer every part the user asked for."
ASKED = "it asked you for something it needs"
QUESTIONS = {
    # a clarifying question ("which city?") is a fine way to end a turn: nothing to judge yet
    "waiting": "Is the assistant asking the user for information it needs before it can answer?",
    "answered_everything": "Does the assistant's answer respond to every question the user asked?",
}


def text_of(message: dict) -> str:
    return "\n".join(block["text"] for block in message["content"] if "text" in block)


def user_turns(messages: list[dict]) -> list[str]:
    """What the user typed, oldest first: skips tool results and our own Guide feedback."""
    texts = [text_of(m) for m in messages if m["role"] == "user"]
    return [t for t in texts if t and FEEDBACK not in t]


def request_state(turns: list[str], answer: str) -> str:
    """What System 1 reads. A short reply like "Istanbul" only makes sense with what came before it."""
    earlier = "".join(f"Earlier, the user said: {t}\n" for t in turns[-3:-1])
    return f"{earlier}User request: {turns[-1] if turns else ''}\n\nAssistant answer: {answer}"


class CompletionCheck(InterventionHandler):
    name = "system1-completion-check"
    MAX_GUIDES = 2  # Guide retries the model, so we must cap it
    PASS = 0.6  # the policy knob: how sure System 1 must be (that it's waiting, or that it answered)
    PAUSE = True  # wait for Enter before asking System 1 (only in a terminal)

    def __init__(self):
        self.guides = 0  # retries used on the current request
        self.judging = None  # the request those retries belong to

    def after_model_call(self, event):
        response = event.stop_response
        if response is None or response.stop_reason != "end_turn":
            return Proceed()  # only judge final answers, not tool-use turns

        turns = user_turns(event.agent.messages)
        request = turns[-1] if turns else ""
        if request != self.judging:  # a new request (in a chat) gets its retries back
            self.judging, self.guides = request, 0
        answer = text_of(response.message)
        short = " ".join(answer.split())
        print(f"\n  check · the model's answer: “{short[:90]}{'…' if len(short) > 90 else ''}”")
        if self.PAUSE:
            wait(f"press Enter to ask {display_name()}")
        p = yes_no_many(request_state(turns, answer), QUESTIONS)  # System 1 observes...
        self.last_probs = p  # lab 11 shows these in the web UI
        self.last_why = None

        # ...plain Python decides.
        if p["waiting"] >= self.PASS:  # it's asking you something: nothing to judge yet
            checklist([("waiting for you?", p["waiting"], True),
                       ("answered everything?", p["answered_everything"], None)], threshold=self.PASS)
            self.last_why = ASKED
            print(f"  check → Proceed: {ASKED}")
            return Proceed()
        checklist([("waiting for you?", p["waiting"], True),
                   ("answered everything?", p["answered_everything"], p["answered_everything"] >= self.PASS)],
                  threshold=self.PASS)
        if p["answered_everything"] >= self.PASS:
            print("  check → Proceed: the answer goes to the user")
            return Proceed()
        if self.guides >= self.MAX_GUIDES:
            print(f"  check → Proceed: out of retries ({self.MAX_GUIDES}), the answer goes to the user as it is")
            return Proceed()
        self.guides += 1
        print(f"  check → Guide ({self.guides}/{self.MAX_GUIDES}): finish the rest of the request")
        return Guide(feedback=FEEDBACK)


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
