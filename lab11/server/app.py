# Lab 11: the finished travel assistant behind a web API. The React app in lab11/web talks to it.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "labs"))  # labs 7-8 and common/

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import make_agent  # noqa: E402
from common import config  # noqa: E402
from common.config import MAIN_MODEL, check_ollama  # noqa: E402
from common.system1 import unavailable  # noqa: E402
from events import WebCheck, WebGate, decision  # noqa: E402,F401  (re-exported for tests)

SYSTEM1_CHOICES = [("ollama/qwen3.5:4b", "Qwen stand-in"), ("jev", "Jev"), ("kev", "Kev"), ("laya", "Laya")]


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
