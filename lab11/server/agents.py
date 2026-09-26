# Lab 11: build the finished travel assistant as a harness agent.
from pathlib import Path

from strands_harness import create_harness

from events import TurnHandlers

# Eager on purpose, like lab 7, so you can watch the gate catch a guessed city.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, immediately fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "If no city is given, assume Seattle."
)


def make_agent(turn: TurnHandlers, chat_id: str, settings: dict, data: Path):
    return create_harness(
        model=settings["model"],
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch", "read"],  # read: files the user attaches
        session={"id": chat_id, "dir": str(data / "sessions")},  # the chat history, saved to disk
        memory=True,
        skills=True,
        interventions=[turn.gate, turn.check],
        callback_handler=None,  # the browser shows the reply, not the terminal
    )
