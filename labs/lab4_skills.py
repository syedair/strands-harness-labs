# Lab 4: skills — teach the assistant a repeatable task with a markdown file, not code.
from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=True,  # NEW: loads .agent/skills/* on demand
    )

    agent("I'm going to Istanbul next week for 4 days. What should I pack?")


if __name__ == "__main__":
    main()
