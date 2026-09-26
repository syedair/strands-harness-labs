# Lab 11: the finished travel assistant behind a web API. The React chat UI in web/ talks to it.
import json

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands.interventions import Deny, Proceed
from strands_harness import create_harness

from common import config
from common.config import MAIN_MODEL, check_ollama
from common.system1 import unavailable
from lab7_tool_call_gate import ToolCallGate
from lab8_completion_check import CompletionCheck

# Eager on purpose, like lab 7, so you can watch the gate catch a guessed city.
INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, immediately fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "If no city is given, assume Seattle."
)
SYSTEM1_CHOICES = [("ollama/qwen3.5:4b", "Qwen stand-in"), ("jev", "Jev"), ("kev", "Kev"), ("laya", "Laya")]


def decision(source: str, action, probs: dict[str, float]) -> dict:
    kind = "proceed" if isinstance(action, Proceed) else "deny" if isinstance(action, Deny) else "guide"
    return {"type": "decision", "source": source, "action": kind,
            "probs": {key: round(value, 2) for key, value in probs.items()}}


class WebGate(ToolCallGate):
    """Lab 7's gate, plus: record the tool call and the decision for the UI."""

    def __init__(self, events: list[dict]):
        super().__init__()
        self.events = events

    def before_tool_call(self, event):
        action = super().before_tool_call(event)
        self.events.append({"type": "tool", "name": event.tool_use["name"], "input": event.tool_use.get("input", {})})
        self.events.append(decision("gate", action, self.last_probs))
        return action


class WebCheck(CompletionCheck):
    """Lab 8's completion check, plus: record the decision when it judged a final answer."""

    def __init__(self, events: list[dict]):
        super().__init__()
        self.events = events

    def after_model_call(self, event):
        self.last_probs = None
        action = super().after_model_call(event)
        if self.last_probs is not None:
            self.events.append(decision("check", action, self.last_probs))
        return action


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


SESSIONS: dict[str, tuple] = {}  # session_id -> (agent, pending events)
app = FastAPI(title="Travel assistant")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system1_model: str = config.SYSTEM1_MODEL


def line(event: dict) -> str:
    return json.dumps(event) + "\n"


@app.get("/api/system1")
def system1_options():
    options = []
    for model_id, label in SYSTEM1_CHOICES:
        reason = unavailable(model_id)
        options.append({"id": model_id, "label": label, "available": reason is None, "reason": reason})
    return {"default": config.SYSTEM1_MODEL, "options": options}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def stream():
        problem = unavailable(request.system1_model)
        if problem:
            yield line({"type": "error", "message": problem})
            return
        config.SYSTEM1_MODEL = request.system1_model  # one local user: a process-wide switch is fine
        if request.session_id not in SESSIONS:
            events: list[dict] = []
            SESSIONS[request.session_id] = (make_agent(events), events)
        agent, events = SESSIONS[request.session_id]
        try:
            async for event in agent.stream_async(request.message):
                while events:  # decisions recorded by the gate/check since the last event
                    yield line(events.pop(0))
                if event.get("data"):
                    yield line({"type": "text", "delta": event["data"]})
            while events:
                yield line(events.pop(0))
            yield line({"type": "done"})
        except Exception as error:  # show it in the chat instead of breaking the stream
            events.clear()
            yield line({"type": "error", "message": str(error)})

    return StreamingResponse(stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    check_ollama(MAIN_MODEL)
    uvicorn.run(app, host="127.0.0.1", port=8000)
