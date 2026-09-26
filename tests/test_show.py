from types import SimpleNamespace

from common.show import bar, show

CONVERSATION = 'user: What\'s the weather?\nassistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")'
QUESTIONS = {
    "named_city": SimpleNamespace(instructions="Did the user say which city they mean?"),
    "intent": SimpleNamespace(instructions="What does the user want?"),
    "urgency": SimpleNamespace(instructions="How urgent is the request?"),
}
ANSWERS = {
    "named_city": SimpleNamespace(type="noul", noul=0.08),
    "intent": SimpleNamespace(type="choice", choice="weather",
                              probabilities={"itinerary": 0.0, "packing": 0.0, "weather": 1.0}),
    "urgency": SimpleNamespace(type="score", score=1.6, legend={0: "not urgent", 1: "today", 2: "right now"},
                               probabilities={0: 0.16, 1: 0.08, 2: 0.76}),
}


def test_bar_fills_in_proportion():
    assert bar(0.5, width=10) == "█████░░░░░"
    assert bar(0.0, width=4) == "░░░░"
    assert bar(1.0, width=4) == "████"


def test_bar_marks_the_threshold():
    assert bar(0.08, width=20, threshold=0.5) == "██░░░░░░░░│░░░░░░░░░"


def test_show_draws_every_answer_type(capsys):
    show(CONVERSATION, QUESTIONS, ANSWERS)
    out = capsys.readouterr().out
    assert "What's the weather?" in out
    assert "Did the user say which city they mean?" in out and "0.08" in out
    for option in ("weather", "packing", "itinerary", "not urgent", "today", "right now"):
        assert option in out
    assert "0.76" in out and "1.60" in out  # each level, then the weighted score
    assert "\x1b[" not in out  # no colour codes when the output isn't a terminal


def test_show_lists_choice_options_best_first(capsys):
    show(CONVERSATION, QUESTIONS, ANSWERS)
    out = capsys.readouterr().out
    assert out.index("weather ") < out.index("packing") and out.index("weather ") < out.index("itinerary")


def test_pause_shows_the_conversation_and_never_waits_off_a_terminal(capsys, monkeypatch):
    from common.show import pause

    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(AssertionError("waited")))
    pause(CONVERSATION)
    out = capsys.readouterr().out
    assert "What's the weather?" in out and "wttr.in/Seattle" in out


def test_show_can_skip_the_conversation_line(capsys):
    show(CONVERSATION, QUESTIONS, ANSWERS, header=False)
    assert "What's the weather?" not in capsys.readouterr().out
