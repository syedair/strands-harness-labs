# Lab 1: your first harness — one call gives you a ready-made agent.
from strands import Agent
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = "You are a friendly travel assistant. Keep answers short and practical."


def main() -> None:
    check_ollama(MAIN_MODEL)

    # The old way (strands-agents-labs, lab 1): you assemble the agent yourself.
    plain = Agent(system_prompt=INSTRUCTIONS)
    print(f"Hand-built Agent tools: {plain.tool_names}")

    # The harness way: one call, tested defaults. We switch the extras off for now;
    # each later lab turns on exactly one of them.
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=[],
        session=False,
        memory=False,
        skills=False,
    )
    print(f"Harness agent is a {type(agent).__name__} running on {MAIN_MODEL}\n")

    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    agent("I have a free weekend in March. Suggest one city break from London and why.")


if __name__ == "__main__":
    main()
