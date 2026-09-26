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
