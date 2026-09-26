# Lab 11: build the finished travel assistant as a harness agent.
from pathlib import Path

from strands_harness import create_harness

import connectors
import memory
from events import TurnHandlers

# Lab 7 used an eager "assume Seattle" prompt to provoke the gate. The finished assistant uses memory instead.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch and report only what it returns.\n"
    "If the user doesn't say which city, use what you remember about them; if you don't know, ask."
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
