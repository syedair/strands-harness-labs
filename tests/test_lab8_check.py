from types import SimpleNamespace

import lab8_completion_check as lab8


def final_answer_event(answer):
    return SimpleNamespace(
        stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": answer}]}),
        agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": "Weather and packing?"}]}]),
    )


def test_check_records_last_probs(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no", lambda state, question: 0.16)
    check = lab8.CompletionCheck()
    check.after_model_call(final_answer_event("It's 21°C."))
    assert check.last_probs == {"answered_everything": 0.16}


def test_a_question_back_to_the_user_is_not_judged(monkeypatch):
    def must_not_ask(state, question):
        raise AssertionError("the classifier should not be asked")

    monkeypatch.setattr(lab8, "yes_no", must_not_ask)
    check = lab8.CompletionCheck()
    action = check.after_model_call(final_answer_event("Which city would you like the weather for?"))
    assert type(action).__name__ == "Proceed"
    assert check.guides == 0


def test_check_prints_a_bar_and_the_decision(monkeypatch, capsys):
    monkeypatch.setattr(lab8, "yes_no", lambda state, question: 0.02)
    lab8.CompletionCheck().after_model_call(final_answer_event("It's 21°C."))
    out = capsys.readouterr().out
    assert "answered everything?" in out and "0.02" in out and "✗" in out
    assert "check → Guide" in out


def test_the_web_app_check_never_waits_for_enter():
    from events import WebCheck

    assert lab8.CompletionCheck.PAUSE is True and WebCheck.PAUSE is False


def chat_event(answer, messages):
    return SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": answer}]}),
                           agent=SimpleNamespace(messages=messages))


def user(text):
    return {"role": "user", "content": [{"text": text}]}


def test_a_question_in_the_middle_of_the_reply_is_not_judged(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no", lambda s, q: (_ for _ in ()).throw(AssertionError("judged")))
    answer = "Could you please tell me which city? Once you tell me, I'll fetch the forecast."
    assert type(lab8.CompletionCheck().after_model_call(final_answer_event(answer))).__name__ == "Proceed"


def test_in_a_chat_the_latest_request_is_judged_not_the_first_or_our_feedback(monkeypatch):
    seen = []
    monkeypatch.setattr(lab8, "yes_no", lambda state, q: seen.append(state) or 0.9)
    messages = [user("hi"), {"role": "assistant", "content": [{"text": "Hello!"}]},
                user("Weather in Istanbul, and what to pack?"), user(lab8.FEEDBACK)]
    lab8.CompletionCheck().after_model_call(chat_event("It's 20°C.", messages))
    assert "Weather in Istanbul, and what to pack?" in seen[0]
    assert "hi" not in seen[0].split("\n")[0] and lab8.FEEDBACK not in seen[0]


def test_a_new_request_gets_its_retries_back(monkeypatch):
    monkeypatch.setattr(lab8, "yes_no", lambda s, q: 0.1)
    check = lab8.CompletionCheck()
    first = [user("Weather and packing?")]
    for _ in range(check.MAX_GUIDES):
        check.after_model_call(chat_event("It's 20°C.", first))
    action = check.after_model_call(chat_event("It's 20°C.", first + [user("Weather in Rome and what to wear?")]))
    assert type(action).__name__ == "Guide"
