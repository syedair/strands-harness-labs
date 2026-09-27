# Lab 2: built-in tools — the assistant looks up the real forecast with no tool code written.
from strands_harness import create_harness

from common.chat import chat, wants_chat
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
        builtin_tools=["web_fetch", "read", "write"],  # NEW: pin exactly the tools we want
        session=False,
        memory=False,
        skills=False,
    )
    print(f"Tools this agent can use: {agent.tool_names}\n")

    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    agent("What's the weather in Rome right now?")


if __name__ == "__main__":
    main()
