# Lab 3: sessions & memory — the assistant remembers where you live, across runs.
import sys

from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch.\n"
    "When the user tells you a lasting personal fact (home city, preferences), save it to memory."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session={"id": "travel"},  # NEW: conversation saved under .agent/sessions/travel
        memory=True,  # NEW: long-term notes saved as markdown under .agent/memory
        skills=False,
    )

    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    # Run 1: uv run labs/lab3_sessions_memory.py tell
    # Run 2: uv run labs/lab3_sessions_memory.py ask   (a fresh process — nothing in RAM)
    if sys.argv[1:] == ["tell"]:
        agent("By the way, I live in London.")
    else:
        agent("What's the weather like at home today?")


if __name__ == "__main__":
    main()
