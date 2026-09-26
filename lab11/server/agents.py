# Lab 11: build the finished travel assistant as a harness agent.
from strands_harness import create_harness

from common.config import MAIN_MODEL
from events import WebCheck, WebGate

# Eager on purpose, like lab 7, so you can watch the gate catch a guessed city.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, immediately fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "If no city is given, assume Seattle."
)


def make_agent(events: list[dict]):
    return create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,  # the server keeps each chat in memory
        memory=True,
        skills=True,
        interventions=[WebGate(events), WebCheck(events)],
        callback_handler=None,  # the browser shows the reply, not the terminal
    )
