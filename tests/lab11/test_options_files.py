import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402
import chats  # noqa: E402

PROMPTS: list[str] = []


class PromptAgent:
    def __init__(self, turn, chat_id, settings, data):
        self.messages = []

    async def stream_async(self, message):
        PROMPTS.append(message)
        yield {"data": "ok"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    PROMPTS.clear(); server.AGENTS.clear()
    monkeypatch.setattr(server, "STORE", chats.ChatStore(tmp_path))
    monkeypatch.setattr(server, "DATA", tmp_path)
    monkeypatch.setattr(server.config, "SYSTEM1_MODEL", "ollama/qwen3.5:4b")
    monkeypatch.setattr(server, "make_agent", PromptAgent)
    monkeypatch.setattr(server, "unavailable", lambda model: "Model isn't pulled" if "gpt-oss" in model else None)
    monkeypatch.setattr(server, "bedrock_ready", lambda: True)
    return TestClient(server.app)


def test_options_list_models_system1_and_availability(client):
    body = client.get("/api/options").json()
    ids = [m["id"] for m in body["models"]]
    assert ids == ["bedrock/moonshotai.kimi-k2.5", "bedrock/nvidia.nemotron-super-3-120b",
                   "bedrock/us.anthropic.claude-sonnet-5", "bedrock/us.moonshotai.kimi-k3", "ollama/gpt-oss:20b"]
    local = body["models"][-1]
    assert local["available"] is False and local["reason"] == "Model isn't pulled"
    assert [o["id"] for o in body["system1"]["options"]] == ["ollama/qwen3.5:4b", "jev", "kev", "laya"]


def test_upload_saves_file_and_next_message_mentions_it(client, tmp_path):
    chat_id = client.post("/api/chats").json()["id"]
    saved = client.post(f"/api/chats/{chat_id}/files", files={"file": ("plan.md", b"# Day 1\nBosphorus cruise", "text/markdown")}).json()
    assert saved["name"] == "plan.md" and saved["size"] == 24
    assert (tmp_path / "files" / chat_id / "plan.md").read_text().startswith("# Day 1")
    client.post(f"/api/chats/{chat_id}/messages", json={"message": "What's on day 1?"})
    assert PROMPTS[0].startswith("What's on day 1?") and f"Attached file: {saved['path']}" in PROMPTS[0]
    client.post(f"/api/chats/{chat_id}/messages", json={"message": "Thanks"})
    assert "Attached file" not in PROMPTS[1]  # only the next message carries it
    assert [f["name"] for f in client.get(f"/api/chats/{chat_id}").json()["files"]] == ["plan.md"]


def test_upload_rejects_wrong_type_and_big_files(client):
    chat_id = client.post("/api/chats").json()["id"]
    assert client.post(f"/api/chats/{chat_id}/files", files={"file": ("run.exe", b"x", "application/octet-stream")}).status_code == 415
    big = b"x" * (5 * 1024 * 1024 + 1)
    assert client.post(f"/api/chats/{chat_id}/files", files={"file": ("big.txt", big, "text/plain")}).status_code == 413
