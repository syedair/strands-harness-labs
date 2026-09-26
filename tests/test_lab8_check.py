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
