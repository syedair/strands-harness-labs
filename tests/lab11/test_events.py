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
    turn.start_turn("Pack for 4 days in Istanbul and check the weather")
    turn.check.after_model_call(final("Here is your list."))
    assert "Pack for 4 days in Istanbul and check the weather" in seen[0] and "What's the weather?" not in seen[0]


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


def test_gate_counts_recalled_memories_as_known_facts(monkeypatch):
    seen = []
    monkeypatch.setattr(lab7, "yes_no_many", lambda state, q: seen.append(state) or {
        "matches_intent": 0.9, "missing_info": 0.1, "args_grounded": 0.9, "premature": 0.1})
    turn = events.TurnHandlers([])
    turn.start_turn("What's the weather at home?")
    turn.recall(["home.md"], ["The user lives in Dubai."])
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {"url": "https://wttr.in/Dubai"}},
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "What's the weather at home?"}]}]))
    turn.gate.before_tool_call(call)
    assert "The user lives in Dubai." in seen[0]


def test_same_recall_twice_in_a_turn_is_one_event():
    log = []
    turn = events.TurnHandlers(log)
    turn.start_turn("hi")
    turn.recall(["home.md", "trip.md"], ["Dubai", "Istanbul"]); turn.recall(["trip.md", "home.md"], ["Istanbul", "Dubai"])
    assert [e["ids"] for e in log if e["type"] == "memory"] == [["home.md", "trip.md"]]


def test_the_finished_assistant_uses_memory_not_a_default_city():
    import agents
    assert "Seattle" not in agents.INSTRUCTIONS
    assert "remember" in agents.INSTRUCTIONS


def test_recall_event_says_what_was_searched_and_how_relevant():
    log = []
    turn = events.TurnHandlers(log)
    turn.start_turn("What's my name?")
    turn.recall(["name.md"], ["The user's name is Syed."], [0.95], "What's my name?")
    assert log == [{"type": "memory", "ids": ["name.md"], "scores": [0.95], "query": "What's my name?"}]


def test_saving_a_note_is_an_event():
    log = []
    events.TurnHandlers(log).stored("home.md")
    assert log == [{"type": "stored", "ids": ["home.md"]}]


def test_recall_query_shows_only_the_users_words():
    log = []
    turn = events.TurnHandlers(log)
    turn.recall(["name.md"], ["Syed"], [0.9], "What is my name?\n\n\n<system-reminder>\n<environment>cwd…</environment>")
    assert log[0]["query"] == "What is my name?"


def test_the_app_leaves_out_the_environment_plugin():
    import inspect
    import agents
    assert 'builtin_plugins=["todos"]' in inspect.getsource(agents.make_agent)


@pytest.mark.parametrize("request_text,judged", [
    ("what's my name", False),
    ("Who am I?", False),
    ("What's the weather in Istanbul, and what should I pack for 4 days there?", True),
    ("Plan 3 days in Rome. Also suggest a hotel?", True),
])
def test_check_only_judges_requests_with_more_than_one_part(monkeypatch, request_text, judged):
    asked = []
    monkeypatch.setattr(lab8, "yes_no", lambda state, q: asked.append(state) or 0.2)
    turn = events.TurnHandlers([])
    turn.start_turn(request_text)
    turn.check.after_model_call(final("An answer."))
    assert bool(asked) == judged


def test_a_check_that_hits_its_retry_limit_says_it_gave_up(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no", lambda state, q: 0.2)
    log = []
    turn = events.TurnHandlers(log)
    turn.start_turn("Weather in Istanbul and what to pack?")
    for _ in range(lab8.CompletionCheck.MAX_GUIDES + 1):
        turn.check.after_model_call(final("Half an answer."))
    last = [e for e in log if e["source"] == "check"][-1]
    assert last["action"] == "proceed" and last["why"] == "gave up after 2 retries"


def test_forget_tool_deletes_notes_and_reports_them(tmp_path):
    (tmp_path / "name.md").write_text("The user's name is John.")
    turn = events.TurnHandlers([])
    forget = events.forget_tool(turn, tmp_path, judge=lambda about, notes: {i: 0.9 for i in notes})
    result = forget(about="my name")
    assert "1" in result and not (tmp_path / "name.md").exists()
    assert turn.events == [{"type": "forgot", "ids": ["name.md"]}] and turn.forgot


def test_forget_tool_says_when_nothing_matched(tmp_path):
    turn = events.TurnHandlers([])
    result = events.forget_tool(turn, tmp_path, judge=lambda about, notes: {})(about="my name")
    assert "nothing" in result.lower() and not turn.forgot and turn.events == []


def test_forget_tool_tells_the_agent_exactly_what_it_deleted(tmp_path):
    (tmp_path / "cruise.md").write_text("User is interested in a Bosphorus cruise.")
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    turn = events.TurnHandlers([])
    judge = lambda about, notes: {i: 0.9 if "Bosphorus" in t else 0.1 for i, t in notes.items()}
    result = events.forget_tool(turn, tmp_path, judge=judge)(about="Istanbul")
    assert "User is interested in a Bosphorus cruise." in result and "Dubai" not in result


def test_forget_tool_asks_for_the_topic_in_the_users_words():
    spec = events.forget_tool(events.TurnHandlers([]), None).tool_spec
    assert "user's own words" in spec["inputSchema"]["json"]["properties"]["about"]["description"]


def test_forget_everything_deletes_every_note(tmp_path):
    for name in ("a.md", "b.md"):
        (tmp_path / name).write_text("A fact.")
    turn = events.TurnHandlers([])
    never = lambda about, notes: pytest.fail("no System 1 needed to forget everything")
    result = events.forget_tool(turn, tmp_path, judge=never)(about="", everything=True)
    assert list(tmp_path.glob("*.md")) == [] and "Deleted 2" in result
    assert sorted(turn.events[0]["ids"]) == ["a.md", "b.md"]
