from types import SimpleNamespace

import pytest

from strands.interventions import Deny, Guide, Proceed

import lab7_tool_call_gate as lab7


def event(city):
    return SimpleNamespace(
        tool_use={"name": "web_fetch", "input": {"url": f"https://wttr.in/{city}?format=3"}},
        agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "What's the weather?"}]}]),
    )


def probs(grounded):
    return lambda state, questions: {"matches_intent": 0.9, "missing_info": 0.1,
                                     "args_grounded": grounded, "premature": 0.1}


def test_repeated_guesses_end_in_deny(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", probs(0.1))
    gate = lab7.ToolCallGate()
    actions = [gate.before_tool_call(event("Seattle")) for _ in range(gate.MAX_BLOCKS + 1)]
    assert all(isinstance(a, Guide) for a in actions[:-1])
    assert isinstance(actions[-1], Deny)


def test_grounded_call_proceeds(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", probs(0.95))
    assert isinstance(lab7.ToolCallGate().before_tool_call(event("Paris")), Proceed)


def test_every_block_prints_a_decision(monkeypatch, capsys):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.1, "missing_info": 0.1,
                                                          "args_grounded": 0.9, "premature": 0.1})
    lab7.ToolCallGate().before_tool_call(event("Paris"))
    assert "gate →" in capsys.readouterr().out


def test_gate_records_last_probs(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", probs(0.2))
    gate = lab7.ToolCallGate()
    gate.before_tool_call(event("Seattle"))
    assert gate.last_probs["args_grounded"] == 0.2


def test_block_carries_its_reason(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.3, "missing_info": 0.1,
                                                          "args_grounded": 0.9, "premature": 0.1})
    action = lab7.ToolCallGate().before_tool_call(event("Paris"))
    assert action.reason == "the tool doesn't match the request"


@pytest.mark.parametrize("probs_seen", [
    {"matches_intent": 0.1, "missing_info": 0.1, "args_grounded": 0.9, "premature": 0.1},
    {"matches_intent": 0.9, "missing_info": 0.1, "args_grounded": 0.1, "premature": 0.1},
    {"matches_intent": 0.9, "missing_info": 0.1, "args_grounded": 0.9, "premature": 0.9},
])
def test_every_block_says_nothing_ran(monkeypatch, probs_seen):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: probs_seen)
    action = lab7.ToolCallGate().before_tool_call(event("Paris"))
    assert "didn't run" in action.feedback and "Don't report" in action.feedback


def test_intent_question_is_concrete_about_weather_helping_with_packing():
    # a weather lookup helps a packing request; "a sensible step towards answering" scored 0.21-0.43 on Kev
    question = lab7.QUESTIONS["matches_intent"]
    assert "help answer" in question and "weather forecast helps decide what to pack" in question


def test_the_web_app_gate_never_waits_for_enter():
    from events import WebGate

    assert lab7.ToolCallGate.PAUSE is True and WebGate.PAUSE is False
