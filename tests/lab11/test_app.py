import json
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")  # lab 11 needs: uv sync --extra web

from fastapi.testclient import TestClient  # noqa: E402
from strands.interventions import Guide, Proceed  # noqa: E402

import app as server  # noqa: E402


class FakeAgent:
    """Streams two text deltas; the 'gate' records a decision in between."""

    def __init__(self, events, fail=False):
        self.events, self.fail = events, fail

    async def stream_async(self, message):
        yield {"data": "Checking "}
        self.events.append({"type": "tool", "name": "web_fetch", "input": {"url": "https://wttr.in/Paris"}})
        self.events.append(server.decision("gate", Proceed(), {"args_grounded": 0.94}))
        if self.fail:
            raise RuntimeError("Bedrock throttled")
        yield {"data": "Paris: sunny."}


@pytest.fixture
def client(monkeypatch):
    server.SESSIONS.clear()
    monkeypatch.setattr(server.config, "SYSTEM1_MODEL", "ollama/qwen3.5:4b")  # restored after each test
    monkeypatch.setattr(server, "make_agent", lambda events: FakeAgent(events))
    monkeypatch.setattr(server, "unavailable", lambda model: None)
    return TestClient(server.app)


def chat(client, session="s1", model="ollama/qwen3.5:4b"):
    response = client.post("/api/chat", json={"session_id": session, "message": "Weather in Paris?",
                                               "system1_model": model})
    return [json.loads(line) for line in response.text.splitlines()]


def test_stream_has_text_tool_decision_in_order(client):
    events = chat(client)
    assert [e["type"] for e in events] == ["text", "tool", "decision", "text", "done"]
    assert events[2] == {"type": "decision", "source": "gate", "action": "proceed", "why": None, "p": 0.94,
                         "probs": {"args_grounded": 0.94}}


def test_same_session_reuses_agent_and_new_session_gets_a_new_one(client):
    chat(client, "a"); chat(client, "a"); chat(client, "b")
    assert set(server.SESSIONS) == {"a", "b"}


def test_unavailable_system1_returns_one_error(client, monkeypatch):
    monkeypatch.setattr(server, "unavailable", lambda model: "Jev needs TYPESAFE_API_KEY")
    assert chat(client, model="jev") == [{"type": "error", "message": "Jev needs TYPESAFE_API_KEY"}]


def test_agent_failure_ends_stream_with_error(client, monkeypatch):
    monkeypatch.setattr(server, "make_agent", lambda events: FakeAgent(events, fail=True))
    events = chat(client)
    assert events[-1] == {"type": "error", "message": "Bedrock throttled"}


def test_selected_system1_model_is_applied(client):
    chat(client, model="kev")
    assert server.config.SYSTEM1_MODEL == "kev"


def test_system1_options_report_availability(client, monkeypatch):
    monkeypatch.setattr(server, "unavailable", lambda m: "Kev isn't running" if m == "kev" else None)
    body = client.get("/api/system1").json()
    kev = next(o for o in body["options"] if o["id"] == "kev")
    assert kev == {"id": "kev", "label": "Kev", "available": False, "reason": "Kev isn't running"}
    assert [o["id"] for o in body["options"]] == ["ollama/qwen3.5:4b", "jev", "kev", "laya"]


def test_decision_maps_actions():
    assert server.decision("gate", Guide(feedback="x"), {"a": 0.341})["action"] == "guide"
    assert server.decision("check", Proceed(), {"answered_everything": 0.781})["probs"] == {"answered_everything": 0.78}
    assert server.decision("gate", Proceed(), {})["p"] is None  # missing probability: no crash


def test_web_gate_records_tool_and_decision(monkeypatch):
    import lab7_tool_call_gate as lab7
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.9, "missing_info": 0.1,
                                                          "args_grounded": 0.1, "premature": 0.1})
    events = []
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {"url": "https://wttr.in/Seattle"}},
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "Weather?"}]}]))
    server.WebGate(events).before_tool_call(call)
    assert [e["type"] for e in events] == ["tool", "decision"]
    assert events[1]["action"] == "guide"


def test_web_check_records_only_judged_turns(monkeypatch):
    import lab8_completion_check as lab8
    monkeypatch.setattr(lab8, "yes_no", lambda s, q: 0.2)
    events = []
    check = server.WebCheck(events)
    tool_turn = SimpleNamespace(stop_response=SimpleNamespace(stop_reason="tool_use", message={"content": []}),
                                agent=SimpleNamespace(messages=[]))
    check.after_model_call(tool_turn)
    assert events == []
    final = SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": "21°C"}]}),
                            agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "Weather and packing?"}]}]))
    check.after_model_call(final)
    assert events[0]["source"] == "check" and events[0]["action"] == "guide"


def test_decision_names_the_rule_and_its_probability():
    guess = server.decision("gate", Guide(feedback="x", reason="ask the user instead of guessing"),
                            {"matches_intent": 0.9, "args_grounded": 0.341})
    assert guess["why"] == "ask the user instead of guessing" and guess["p"] == 0.34
    intent = server.decision("gate", Guide(feedback="x", reason="the tool doesn't match the request"),
                             {"matches_intent": 0.64, "args_grounded": 0.99})
    assert intent["p"] == 0.64
    allowed = server.decision("gate", Proceed(), {"args_grounded": 0.94})
    assert allowed["why"] is None and allowed["p"] == 0.94
    check = server.decision("check", Proceed(), {"answered_everything": 0.72})
    assert check["p"] == 0.72


def test_web_gate_only_judges_web_fetch(monkeypatch):
    import lab7_tool_call_gate as lab7
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: pytest.fail("skills calls must not be judged"))
    events = []
    call = SimpleNamespace(tool_use={"name": "skills", "input": {"skill_name": "packing-list"}},
                           agent=SimpleNamespace(messages=[]))
    action = server.WebGate(events).before_tool_call(call)
    assert isinstance(action, Proceed)
    assert events == [{"type": "tool", "name": "skills", "input": {"skill_name": "packing-list"}}]
