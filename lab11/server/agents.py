# Lab 11: build the finished travel assistant as a harness agent.
from pathlib import Path

from strands_harness import create_harness
from strands_harness.prompt import build_system_prompt

import connectors
import memory
from events import TurnHandlers, forget_tool

ROOT = Path(__file__).resolve().parents[2]  # the repo: skills live in .agent/skills under it

# Lab 7 used an eager "assume Seattle" prompt to provoke the gate. The finished assistant uses memory instead.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch and report only what it returns.\n"
    "If the user doesn't say which city, use what you remember about them; if you don't know, ask.\n"
    "Memories carry the date they were saved; when two disagree, trust the newer one.\n"
    "When the user asks you to forget something, call forget_memory; say it's forgotten only if it deleted something."
)


# the skills tool reports a relative location, and the read tool only takes absolute paths
SKILL_FILES = (f"\nSkill locations are relative to {ROOT}: .agent/skills/<name>/references/x.md is "
               f"{ROOT / '.agent' / 'skills'}/<name>/references/x.md. Read skill files by that absolute path.")


def make_agent(turn: TurnHandlers, chat_id: str, settings: dict, data: Path):
    chat_dir = data / "files" / chat_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    mcp = connectors.mcp_config(settings["connectors"], chat_dir, connectors.load_custom(data))
    notes = data / "memory"  # shared by every chat: memory outlives sessions
    notes.mkdir(parents=True, exist_ok=True)
    turn.on_recall = lambda ids: memory.record_hits(notes, ids)
    store = memory.store_for(settings["model"], notes, on_search=turn.recall, on_store=turn.stored,
                             relevance=memory.system1_relevance)  # System 1 decides which memories are relevant
    agent = create_harness(
        model=settings["model"],
        instructions=INSTRUCTIONS,
        tools=[forget_tool(turn, notes)],  # the harness only adds memories; this deletes them
        builtin_tools=["web_fetch", "read"],  # read: files the user attaches
        session={"id": chat_id, "dir": str(data / "sessions")},  # the chat history, saved to disk
        memory={"stores": [store]},  # the harness's memory, watched so the UI sees each recall
        skills=True,
        builtin_plugins=["todos"],  # no "environment": the app doesn't need the working directory in every prompt
        mcp_servers=mcp or None,  # connectors the user turned on
        interventions=[turn.gate, turn.check],
        callback_handler=None,  # the browser shows the reply, not the terminal
    )
    # a reopened session restores the system prompt it was saved with; use today's instructions instead
    agent.system_prompt = build_system_prompt(INSTRUCTIONS + SKILL_FILES)
    return agent
