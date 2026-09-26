# Lab 5: interventions — the assistant asks before it writes a file.
import sys
from pathlib import Path

from strands.vended_interventions.hitl import HumanInTheLoop
from strands_harness import create_harness, resolve_interventions

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama

TRIPS = Path("trips").resolve()  # the write tool needs an absolute path

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch.\n"
    f"Save packing lists to {TRIPS}/<city>-packing-list.md."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    TRIPS.mkdir(exist_ok=True)

    if sys.argv[1:] == ["policy"]:
        # Part B: a plain-English rule. A classifier decides which calls need your approval.
        interventions = resolve_interventions(
            "Reading and fetching are fine. Writing files is only fine under ./trips.",
            ask="stdio",
        )
    else:
        # Part A: approve every tool call in the terminal.
        interventions = HumanInTheLoop(ask="stdio")

    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch", "write"],
        session=False,
        memory=False,
        skills=True,
        interventions=interventions,  # NEW
    )

    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    agent("Make me a packing list for 4 days in Istanbul and save it.")


if __name__ == "__main__":
    main()
