import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402
import chats  # noqa: E402

HISTORY: dict[str, list] = {}  # stands in for the harness's session files
BUILDS: list[tuple] = []


class HistoryAgent:
    """Keeps messages per chat id, like the harness's session persistence."""

    def __init__(self, turn, chat_id, settings, data):
        self.turn, self.chat_id = turn, chat_id
        self.messages = HISTORY.setdefault(chat_id, [])
        BUILDS.append((chat_id, settings["model"]))

    async def stream_async(self, message):
        self.messages.append({"role": "user", "content": [{"text": message}]})
        yield {"data": f"echo: {message}"}
        self.messages.append({"role": "assistant", "content": [{"text": f"echo: {message}"}]})


@pytest.fixture
def client(monkeypatch, tmp_path):
    HISTORY.clear(); BUILDS.clear(); server.AGENTS.clear()
    monkeypatch.setattr(server, "STORE", chats.ChatStore(tmp_path))
    monkeypatch.setattr(server.config, "SYSTEM1_MODEL", "ollama/qwen3.5:4b")
    monkeypatch.setattr(server, "make_agent", HistoryAgent)
    monkeypatch.setattr(server, "unavailable", lambda model: None)
    return TestClient(server.app)


def send(client, chat_id, message, **settings):
    response = client.post(f"/api/chats/{chat_id}/messages", json={"message": message, **settings})
    return [json.loads(line) for line in response.text.splitlines()]


def test_first_reply_sets_the_title(client):
    chat_id = client.post("/api/chats").json()["id"]
    events = send(client, chat_id, "What's the weather in Paris tomorrow afternoon?")
    assert {"type": "title", "title": "What's the weather in Paris tomorrow…"} in events
    assert client.get("/api/chats").json()[0]["title"] == "What's the weather in Paris tomorrow…"


def test_history_survives_a_restart(client):
    chat_id = client.post("/api/chats").json()["id"]
    send(client, chat_id, "hi")
    server.AGENTS.clear()  # a new server process: no agents in memory
    turns = client.get(f"/api/chats/{chat_id}").json()["turns"]
    assert turns == [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "echo: hi"}]


def test_switching_model_rebuilds_on_the_same_history(client):
    chat_id = client.post("/api/chats").json()["id"]
    send(client, chat_id, "one")
    send(client, chat_id, "two", model="bedrock/us.moonshotai.kimi-k3")
    assert [b[1] for b in BUILDS] == [server.config.MAIN_MODEL, "bedrock/us.moonshotai.kimi-k3"]
    assert len(client.get(f"/api/chats/{chat_id}").json()["turns"]) == 4


def test_delete_removes_the_chat(client):
    chat_id = client.post("/api/chats").json()["id"]
    client.delete(f"/api/chats/{chat_id}")
    assert client.get("/api/chats").json() == []
    assert client.get(f"/api/chats/{chat_id}").status_code == 404


def test_rebuilding_for_another_model_makes_tool_ids_portable(client):
    chat_id = client.post("/api/chats").json()["id"]
    send(client, chat_id, "one")
    HISTORY[chat_id].append({"role": "assistant", "content": [{"toolUse": {"toolUseId": "functions.read:0", "name": "read", "input": {}}}]})
    send(client, chat_id, "two", model="bedrock/us.anthropic.claude-sonnet-5")
    assert HISTORY[chat_id][2]["content"][0]["toolUse"]["toolUseId"] == "functions_read_0"
