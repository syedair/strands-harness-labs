# Lab 11: the finished travel assistant behind a web API. The React app in lab11/web talks to it.
import json
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "labs"))  # labs 7-8 and common/

import uvicorn  # noqa: E402
from fastapi import FastAPI, File, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents import make_agent  # noqa: E402
import connectors  # noqa: E402
import memory  # noqa: E402
from chats import ChatStore, title_for, turns_from_messages  # noqa: E402
from common import config  # noqa: E402
from common.config import MAIN_MODEL, check_ollama  # noqa: E402
from common.system1 import unavailable  # noqa: E402
from events import TurnHandlers, WebCheck, WebGate, decision  # noqa: E402,F401  (re-exported for tests)

SYSTEM1_CHOICES = [("ollama/qwen3.5:4b", "Qwen stand-in"), ("jev", "Jev"), ("kev", "Kev"), ("laya", "Laya")]
MODEL_CHOICES = [
    ("bedrock/moonshotai.kimi-k2.5", "Kimi K2.5"),
    ("bedrock/nvidia.nemotron-super-3-120b", "Nemotron Super"),
    ("bedrock/us.anthropic.claude-sonnet-5", "Claude Sonnet 5"),
    ("bedrock/us.moonshotai.kimi-k3", "Kimi K3"),
    ("ollama/gpt-oss:20b", "gpt-oss 20B (local)"),
]
UPLOAD_TYPES = {".txt", ".md", ".csv", ".json", ".pdf"}
UPLOAD_LIMIT = 5 * 1024 * 1024  # 5 MB

DATA = Path(__file__).resolve().parents[1] / "data"  # chats, sessions, files, memory (git-ignored)
STORE = ChatStore(DATA)
AGENTS: dict[str, tuple] = {}  # chat_id -> (agent, TurnHandlers, settings it was built with)
CONNECTOR_ERRORS: dict[str, list[dict]] = {}  # chat_id -> connectors that failed to start
SKILLS = Path(__file__).resolve().parents[2] / ".agent" / "skills"
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
    CONNECTOR_ERRORS[chat_id] = []
    try:
        with capture_logs() as logged:
            agent = make_agent(turn, chat_id, settings, DATA)
        # the harness logs a failing MCP server and carries on, so check which connectors added no tools
        reasons = [m.split("error=<", 1)[1].split(">", 1)[0] for m in logged if "MCP server failed" in m and "error=<" in m]
        CONNECTOR_ERRORS[chat_id] = [
            {"id": c, "error": reasons.pop(0) if reasons else "didn't start (see the server log)"}
            for c in settings["connectors"] if not any(t.startswith(f"{c}_") for t in agent.tool_names)
        ]
    except Exception as error:
        if not settings["connectors"]:
            raise
        # a connector didn't start: keep the chat working without connectors, and say which one failed
        CONNECTOR_ERRORS[chat_id] = [{"id": c, "error": str(error)} for c in settings["connectors"]]
        agent = make_agent(turn, chat_id, {**settings, "connectors": []}, DATA)
    AGENTS[chat_id] = (agent, turn, key)
    return agent, turn


@contextmanager
def capture_logs():
    """Collect log messages while building an agent (the harness reports MCP failures this way)."""
    messages: list[str] = []

    class Collect(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    handler = Collect(level=logging.WARNING)
    logging.getLogger().addHandler(handler)
    try:
        yield messages
    finally:
        logging.getLogger().removeHandler(handler)


def require_chat(chat_id: str) -> None:
    if not STORE.exists(chat_id):
        raise HTTPException(404, "No such chat")


def bedrock_ready() -> bool:
    import boto3

    return boto3.Session().get_credentials() is not None


def model_problem(model_id: str) -> str | None:
    if model_id.startswith("bedrock/"):
        return None if bedrock_ready() else "No AWS credentials for Bedrock. Run: aws configure"
    return unavailable(model_id)


@app.get("/api/options")
def options():
    models = []
    for model_id, label in MODEL_CHOICES:
        reason = model_problem(model_id)
        models.append({"id": model_id, "label": label, "available": reason is None, "reason": reason})
    return {"models": models, "default_model": config.MAIN_MODEL, "system1": system1_options()}


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
            "files": STORE.files(chat_id), **STORE.settings(chat_id)}


class ConnectorRequest(BaseModel):
    label: str
    command: str
    args: list[str] = []


class EnabledRequest(BaseModel):
    enabled: list[str]


@app.get("/api/connectors")
def list_connectors():
    return connectors.listing(DATA)


@app.post("/api/connectors")
def add_connector(request: ConnectorRequest):
    return {"id": connectors.save_custom(DATA, request.label, request.command, request.args)}


@app.put("/api/chats/{chat_id}/connectors")
def set_connectors(chat_id: str, request: EnabledRequest):
    require_chat(chat_id)
    STORE.save_settings(chat_id, connectors=request.enabled)
    return {"enabled": request.enabled}


def read_skills() -> list[dict]:
    skills = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        front = path.read_text().split("---")[1] if path.read_text().startswith("---") else ""
        fields = dict(line.split(":", 1) for line in front.strip().splitlines() if ":" in line)
        skills.append({"name": fields.get("name", path.parent.name).strip(), "description": fields.get("description", "").strip()})
    return skills


@app.get("/api/harness")
def harness(chat_id: str):
    """What's inside the chat's harness: tools, skills, session, connectors."""
    require_chat(chat_id)
    agent, _ = agent_for(chat_id)
    settings = STORE.settings(chat_id)
    return {
        "tools": list(agent.tool_names),
        "skills": read_skills(),
        "session": {"id": chat_id, "model": settings["model"], "system1_model": settings["system1_model"],
                    "messages": len(agent.messages), "files": STORE.files(chat_id)},
        "connectors": {"enabled": settings["connectors"], "errors": CONNECTOR_ERRORS.get(chat_id, [])},
    }


@app.get("/api/memory")
def memory_graph():
    return memory.graph(DATA / "memory")


@app.post("/api/chats/{chat_id}/files")
async def upload_file(chat_id: str, file: UploadFile = File(...)):
    require_chat(chat_id)
    name = Path(file.filename or "upload").name
    if Path(name).suffix.lower() not in UPLOAD_TYPES:
        raise HTTPException(415, f"Only {', '.join(sorted(UPLOAD_TYPES))} files")
    data = await file.read(UPLOAD_LIMIT + 1)
    if len(data) > UPLOAD_LIMIT:
        raise HTTPException(413, "Files can be up to 5 MB")
    folder = DATA / "files" / chat_id
    folder.mkdir(parents=True, exist_ok=True)
    path = (folder / name).resolve()  # the read tool needs an absolute path
    path.write_bytes(data)
    info = {"name": name, "path": str(path), "size": len(data)}
    STORE.add_file(chat_id, info)
    return info


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
            prompt = request.message + "".join(f"\n\nAttached file: {p}" for p in STORE.take_pending_files(chat_id))
            async for event in agent.stream_async(prompt):
                while events:  # decisions recorded by the gate/check since the last event
                    yield line(events.pop(0))
                if event.get("data"):
                    yield line({"type": "text", "delta": event["data"]})
            while events:
                yield line(events.pop(0))
            STORE.touch(chat_id)
            yield line({"type": "done"})
            manager = getattr(agent, "memory_manager", None)
            if manager is not None:  # save what this turn taught it; the UI refreshes memory when the stream closes
                await manager.flush()
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
