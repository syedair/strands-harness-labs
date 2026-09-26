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


def test_the_agent_knows_memories_are_saved_for_it():
    assert "saved automatically" in agents.INSTRUCTIONS


def test_knowledge_store_comes_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_DIR", raising=False)
    assert agents.knowledge_for(TurnHandlers([]), tmp_path) is None
    (tmp_path / "Memory").mkdir()
    monkeypatch.setenv("KNOWLEDGE_DIR", str(tmp_path / "Memory"))
    monkeypatch.setenv("KNOWLEDGE_FOLDERS", "Technical, Reference")
    store = agents.knowledge_for(TurnHandlers([]), tmp_path / "data")
    assert store.folders == ["Technical", "Reference"] and store.cache.parent == tmp_path / "data"


def test_the_agent_recalls_from_both_stores(tmp_path, monkeypatch):
    (tmp_path / "Memory").mkdir()
    monkeypatch.setenv("KNOWLEDGE_DIR", str(tmp_path / "Memory"))
    agent = agents.make_agent(TurnHandlers([]), "abcdef012345", SETTINGS, tmp_path / "data")
    names = [s.name for s in agent.memory_manager._stores]
    assert names == ["memory", "knowledge"]
