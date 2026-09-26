import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402
import chats  # noqa: E402
import connectors  # noqa: E402

BUILDS: list[list[str]] = []


class ToolAgent:
    def __init__(self, turn, chat_id, settings, data):
        if "broken" in settings["connectors"]:
            raise RuntimeError("MCP server 'broken' failed to start: command not found")
        BUILDS.append(settings["connectors"])
        self.messages = [{"role": "user", "content": [{"text": "hi"}]}]
        self.tool_names = ["web_fetch", "read"] + [f"{c}_search" for c in settings["connectors"]]

    async def stream_async(self, message):
        yield {"data": "ok"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    BUILDS.clear(); server.AGENTS.clear()
    monkeypatch.setattr(server, "STORE", chats.ChatStore(tmp_path))
    monkeypatch.setattr(server, "DATA", tmp_path)
    monkeypatch.setattr(server, "make_agent", ToolAgent)
    monkeypatch.setattr(server, "unavailable", lambda model: None)
    return TestClient(server.app)


def test_mcp_config_fills_in_the_chat_folder(tmp_path):
    config = connectors.mcp_config(["aws-docs", "files"], tmp_path / "files" / "abc", custom={})
    assert config["aws-docs"]["command"] == "uvx"
    assert config["files"]["args"][-1] == str(tmp_path / "files" / "abc")


def test_custom_connector_is_saved_and_listed(client):
    client.post("/api/connectors", json={"label": "Weather MCP", "command": "uvx", "args": ["weather-mcp"]})
    listed = client.get("/api/connectors").json()
    assert [c["label"] for c in listed if c["custom"]] == ["Weather MCP"]
    assert {"aws-docs", "files"} <= {c["id"] for c in listed}


def test_enabling_a_connector_rebuilds_with_its_tools(client):
    chat_id = client.post("/api/chats").json()["id"]
    client.get(f"/api/harness?chat_id={chat_id}")
    client.put(f"/api/chats/{chat_id}/connectors", json={"enabled": ["aws-docs"]})
    harness = client.get(f"/api/harness?chat_id={chat_id}").json()
    assert BUILDS == [[], ["aws-docs"]]
    assert "aws-docs_search" in harness["tools"]
    assert harness["connectors"] == {"enabled": ["aws-docs"], "errors": []}


def test_a_failing_connector_is_reported_and_the_chat_keeps_working(client):
    chat_id = client.post("/api/chats").json()["id"]
    client.put(f"/api/chats/{chat_id}/connectors", json={"enabled": ["broken"]})
    harness = client.get(f"/api/harness?chat_id={chat_id}").json()
    assert harness["connectors"]["errors"] == [{"id": "broken", "error": "MCP server 'broken' failed to start: command not found"}]
    assert "web_fetch" in harness["tools"]


def test_harness_lists_skills_and_session(client):
    chat_id = client.post("/api/chats").json()["id"]
    harness = client.get(f"/api/harness?chat_id={chat_id}").json()
    assert {"name": "packing-list", "description": "Build a packing list for a trip from the destination, dates, and forecast."} in harness["skills"]
    assert harness["session"]["id"] == chat_id and harness["session"]["messages"] == 1


class SilentFailAgent(ToolAgent):
    """Like the real harness: a failing MCP server is logged, not raised, and adds no tools."""

    def __init__(self, turn, chat_id, settings, data):
        import logging

        logging.getLogger("strands_harness").warning(
            "error=<the client initialization failed: [Errno 2] No such file or directory: 'no-such-mcp'> | "
            "MCP server failed to start, continuing with no tools")
        self.messages = []
        self.tool_names = ["web_fetch", "read"]


def test_a_connector_that_adds_no_tools_is_reported_with_the_logged_reason(client, monkeypatch):
    monkeypatch.setattr(server, "make_agent", SilentFailAgent)
    chat_id = client.post("/api/chats").json()["id"]
    client.put(f"/api/chats/{chat_id}/connectors", json={"enabled": ["aws-docs"]})
    errors = client.get(f"/api/harness?chat_id={chat_id}").json()["connectors"]["errors"]
    assert errors == [{"id": "aws-docs", "error": "the client initialization failed: [Errno 2] No such file or directory: 'no-such-mcp'"}]


def test_a_new_chat_previews_the_harness_before_its_first_message(client):
    harness = client.get("/api/harness").json()
    assert harness["tools"] == ["web_fetch", "read"]
    assert harness["skills"] and harness["connectors"] == {"enabled": [], "errors": []}
    assert harness["session"]["messages"] == 0 and harness["session"]["id"] == ""
    assert client.get("/api/chats").json() == []  # previewing doesn't create a chat
