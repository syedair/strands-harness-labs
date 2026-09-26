# Lab 11: the finished travel assistant behind a web API. The React app in lab11/web talks to it.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "labs"))  # labs 7-8 and common/

import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents import make_agent  # noqa: E402
from chats import ChatStore, title_for, turns_from_messages  # noqa: E402
from common import config  # noqa: E402
from common.config import MAIN_MODEL, check_ollama  # noqa: E402
from common.system1 import unavailable  # noqa: E402
from events import TurnHandlers, WebCheck, WebGate, decision  # noqa: E402,F401  (re-exported for tests)

SYSTEM1_CHOICES = [("ollama/qwen3.5:4b", "Qwen stand-in"), ("jev", "Jev"), ("kev", "Kev"), ("laya", "Laya")]

DATA = Path(__file__).resolve().parents[1] / "data"  # chats, sessions, files, memory (git-ignored)
STORE = ChatStore(DATA)
AGENTS: dict[str, tuple] = {}  # chat_id -> (agent, TurnHandlers, settings it was built with)
app = FastAPI(title="Travel assistant")


class MessageRequest(BaseModel):
    message: str
    model: str | None = None
    system1_model: str | None = None


def line(event: dict) -> str:
    return json.dumps(event) + "\n"


def agent_for(chat_id: str):
    """The chat's agent, rebuilt when its model or connectors change (history comes from the session)."""
    settings = STORE.settings(chat_id)
    key = (settings["model"], tuple(settings["connectors"]))
    cached = AGENTS.get(chat_id)
    if cached and cached[2] == key:
        return cached[0], cached[1]
    turn = TurnHandlers([])
    agent = make_agent(turn, chat_id, settings, DATA)
    AGENTS[chat_id] = (agent, turn, key)
    return agent, turn


def require_chat(chat_id: str) -> None:
    if not STORE.exists(chat_id):
        raise HTTPException(404, "No such chat")


@app.get("/api/system1")
def system1_options():
    options = []
    for model_id, label in SYSTEM1_CHOICES:
        reason = unavailable(model_id)
        options.append({"id": model_id, "label": label, "available": reason is None, "reason": reason})
    return {"default": config.SYSTEM1_MODEL, "options": options}


@app.get("/api/chats")
def list_chats():
    return STORE.list()


@app.post("/api/chats")
def create_chat():
    return {"id": STORE.create()}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    AGENTS.pop(chat_id, None)
    STORE.delete(chat_id)
    return {"ok": True}


@app.get("/api/chats/{chat_id}")
def open_chat(chat_id: str):
    require_chat(chat_id)
    agent, _ = agent_for(chat_id)
    return {"id": chat_id, "title": STORE.title(chat_id), "turns": turns_from_messages(agent.messages),
            **STORE.settings(chat_id)}


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, request: MessageRequest):
    require_chat(chat_id)

    async def stream():
        events: list[dict] = []
        try:
            STORE.save_settings(chat_id, model=request.model, system1_model=request.system1_model)
            settings = STORE.settings(chat_id)
            problem = unavailable(settings["system1_model"])
            if problem:
                yield line({"type": "error", "message": problem})
                return
            config.SYSTEM1_MODEL = settings["system1_model"]  # one local user: a process-wide switch is fine
            agent, turn = agent_for(chat_id)
            events = turn.events
            turn.start_turn(request.message)
            if STORE.title(chat_id) == "New chat":
                STORE.set_title(chat_id, title_for(request.message))
                yield line({"type": "title", "title": STORE.title(chat_id)})
            async for event in agent.stream_async(request.message):
                while events:  # decisions recorded by the gate/check since the last event
                    yield line(events.pop(0))
                if event.get("data"):
                    yield line({"type": "text", "delta": event["data"]})
            while events:
                yield line(events.pop(0))
            STORE.touch(chat_id)
            yield line({"type": "done"})
        except Exception as error:  # show it in the chat instead of breaking the stream
            while events:  # what happened just before the failure explains it
                yield line(events.pop(0))
            yield line({"type": "error", "message": str(error)})
        finally:
            events.clear()

    return StreamingResponse(stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    check_ollama(MAIN_MODEL)
    uvicorn.run(app, host="127.0.0.1", port=8000)
