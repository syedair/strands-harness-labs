import pytest
pytest.importorskip("fastapi")
from types import SimpleNamespace
import lab7_tool_call_gate as lab7
import lab8_completion_check as lab8
import events


def final(answer, first_user="What's the weather?"):
    return SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": answer}]}),
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": first_user}]}]))


def test_check_judges_the_current_message(monkeypatch):
    seen = []
    monkeypatch.setattr(lab8, "yes_no", lambda state, q: seen.append(state) or 0.9)
    turn = events.TurnHandlers([])
    turn.start_turn("Pack for 4 days in Istanbul")
    turn.check.after_model_call(final("Here is your list."))
    assert "Pack for 4 days in Istanbul" in seen[0] and "What's the weather?" not in seen[0]


def test_counters_reset_each_turn(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.9, "missing_info": 0.1,
                                                          "args_grounded": 0.1, "premature": 0.1})
    turn = events.TurnHandlers([])
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {"url": "https://wttr.in/X"}},
                           agent=SimpleNamespace(messages=[]))
    for _ in range(4):
        turn.gate.before_tool_call(call)
    turn.start_turn("again")
    assert turn.gate.blocks == 0 and turn.check.guides == 0


def test_deny_keeps_its_rule(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.9, "missing_info": 0.1,
                                                          "args_grounded": 0.1, "premature": 0.1})
    log = []
    turn = events.TurnHandlers(log)
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {}}, agent=SimpleNamespace(messages=[]))
    for _ in range(lab7.ToolCallGate.MAX_BLOCKS + 1):
        turn.gate.before_tool_call(call)
    last = [e for e in log if e["type"] == "decision"][-1]
    assert last["action"] == "deny" and last["why"] == "ask the user instead of guessing"
