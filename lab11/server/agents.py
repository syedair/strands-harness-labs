# Lab 11: build the finished travel assistant as a harness agent.
from pathlib import Path

from strands_harness import create_harness

import connectors
import memory
from events import TurnHandlers

# Eager on purpose, like lab 7, so you can watch the gate catch a guessed city.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, immediately fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "If no city is given, assume Seattle."
)


def make_agent(turn: TurnHandlers, chat_id: str, settings: dict, data: Path):
    chat_dir = data / "files" / chat_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    mcp = connectors.mcp_config(settings["connectors"], chat_dir, connectors.load_custom(data))
    notes = data / "memory"  # shared by every chat: memory outlives sessions
    notes.mkdir(parents=True, exist_ok=True)
    turn.on_recall = lambda ids: memory.record_hits(notes, ids)
    store = memory.store_for(settings["model"], notes, on_search=turn.recall)
    return create_harness(
        model=settings["model"],
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch", "read"],  # read: files the user attaches
        session={"id": chat_id, "dir": str(data / "sessions")},  # the chat history, saved to disk
        memory={"stores": [store]},  # the harness's memory, watched so the UI sees each recall
        skills=True,
        mcp_servers=mcp or None,  # connectors the user turned on
        interventions=[turn.gate, turn.check],
        callback_handler=None,  # the browser shows the reply, not the terminal
    )
