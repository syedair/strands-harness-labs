from types import SimpleNamespace

import lab8_completion_check as lab8


def user(text):
    return {"role": "user", "content": [{"text": text}]}


def event(answer, messages=None):
    return SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": answer}]}),
                           agent=SimpleNamespace(messages=messages or [user("Weather and packing?")]))


def system1(waiting, answered, seen=None):
    """A stand-in for System 1: the two probabilities the check asks for."""
    def ask(state, questions):
        assert set(questions) == {"waiting", "answered_everything"}
        if seen is not None:
            seen.append(state)
        return {"waiting": waiting, "answered_everything": answered}
    return ask


def test_check_records_last_probs(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.16))
    check = lab8.CompletionCheck()
    check.after_model_call(event("It's 21°C."))
    assert check.last_probs == {"waiting": 0.05, "answered_everything": 0.16}


def test_a_clarifying_question_proceeds(monkeypatch, capsys):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.93, 0.10))
    check = lab8.CompletionCheck()
    action = check.after_model_call(event("Which city are you travelling to?"))
    assert type(action).__name__ == "Proceed" and check.guides == 0
    assert "waiting for you?" in capsys.readouterr().out


def test_an_answer_that_ends_with_an_offer_is_still_judged(monkeypatch, capsys):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.08, 0.91))
    answer = "Istanbul is 20°C: pack layers and an umbrella. Would you like more suggestions?"
    assert type(lab8.CompletionCheck().after_model_call(event(answer))).__name__ == "Proceed"
    out = capsys.readouterr().out
    assert "answered everything?" in out and "0.91" in out and "check → Proceed" in out


def test_half_an_answer_is_sent_back(monkeypatch, capsys):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.02))
    action = lab8.CompletionCheck().after_model_call(event("It's 21°C."))
    out = capsys.readouterr().out
    assert type(action).__name__ == "Guide"
    assert "answered everything?" in out and "0.02" in out and "✗" in out and "check → Guide" in out


def test_retries_are_capped(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.1))
    check = lab8.CompletionCheck()
    actions = [type(check.after_model_call(event("It's 21°C."))).__name__ for _ in range(check.MAX_GUIDES + 1)]
    assert actions == ["Guide"] * check.MAX_GUIDES + ["Proceed"]


def test_in_a_chat_the_latest_request_is_judged_not_the_first_or_our_feedback(monkeypatch):
    seen = []
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.9, seen))
    messages = [user("hi"), {"role": "assistant", "content": [{"text": "Hello!"}]},
                user("Weather in Istanbul, and what to pack?"), user(lab8.FEEDBACK)]
    lab8.CompletionCheck().after_model_call(event("It's 20°C.", messages))
    assert "Weather in Istanbul, and what to pack?" in seen[0]
    assert "User request: hi" not in seen[0] and lab8.FEEDBACK not in seen[0]


def test_a_new_request_gets_its_retries_back(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.1))
    check = lab8.CompletionCheck()
    first = [user("Weather and packing?")]
    for _ in range(check.MAX_GUIDES):
        check.after_model_call(event("It's 20°C.", first))
    action = check.after_model_call(event("It's 20°C.", first + [user("Weather in Rome and what to wear?")]))
    assert type(action).__name__ == "Guide"


def test_the_web_app_check_never_waits_for_enter():
    from events import WebCheck

    assert lab8.CompletionCheck.PAUSE is True and WebCheck.PAUSE is False


def test_a_short_follow_up_is_judged_with_what_the_user_asked_before(monkeypatch):
    seen = []
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.9, seen))
    messages = [user("Travelling tomorrow, what should I pack based on the weather?"),
                {"role": "assistant", "content": [{"text": "Which city?"}]}, user("Istanbul")]
    lab8.CompletionCheck().after_model_call(event("Istanbul is 20°C: pack layers.", messages))
    assert "what should I pack based on the weather?" in seen[0] and "Istanbul" in seen[0]


def test_running_out_of_retries_says_so(monkeypatch, capsys):
    monkeypatch.setattr(lab8, "yes_no_many", system1(0.05, 0.1))
    check = lab8.CompletionCheck()
    for _ in range(check.MAX_GUIDES + 1):
        check.after_model_call(event("It's 21°C."))
    assert "out of retries" in capsys.readouterr().out.splitlines()[-1]
