import pytest
pytest.importorskip("fastapi")
import agents
from events import TurnHandlers

SETTINGS = {"model": "ollama/qwen3.5:4b", "system1_model": "ollama/qwen3.5:4b", "connectors": []}


def test_reopened_chat_gets_the_current_instructions(tmp_path, monkeypatch):
    first = agents.make_agent(TurnHandlers([]), "abcdef012345", SETTINGS, tmp_path)
    first._session_manager.sync_agent(first)  # saves the session, including the system prompt it was built with
    monkeypatch.setattr(agents, "INSTRUCTIONS", "You are the NEW travel assistant.")
    reopened = agents.make_agent(TurnHandlers([]), "abcdef012345", SETTINGS, tmp_path)
    assert "NEW travel assistant" in str(reopened.system_prompt)


def test_the_agent_can_forget(tmp_path):
    agent = agents.make_agent(TurnHandlers([]), "abcdef012345", SETTINGS, tmp_path)
    assert "forget_memory" in agent.tool_names
    assert "forget_memory" in str(agent.system_prompt)


def test_the_agent_knows_where_skill_files_are(tmp_path):
    agent = agents.make_agent(TurnHandlers([]), "abcdef012345", SETTINGS, tmp_path)
    assert str(agents.ROOT / ".agent" / "skills") in str(agent.system_prompt)
