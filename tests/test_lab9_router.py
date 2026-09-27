import asyncio
from types import SimpleNamespace

import lab9_model_switching as lab9


def context(text):
    return SimpleNamespace(attempts=[], messages=[{"role": "user", "content": [{"text": text}]}],
                           candidates=[SimpleNamespace(name="small"), SimpleNamespace(name="big")])


def test_quick_question_goes_to_the_small_model_and_says_so(monkeypatch, capsys):
    monkeypatch.setattr(lab9, "yes_no", lambda state, question: 0.82)
    pick = asyncio.run(lab9.System1Strategy().select(context("What's the weather in Paris?")))
    out = capsys.readouterr().out
    assert pick.name == "small"
    assert "quick question?" in out and "0.82" in out and "router → small" in out


def test_big_request_goes_to_the_big_model(monkeypatch):
    monkeypatch.setattr(lab9, "yes_no", lambda state, question: 0.15)
    assert asyncio.run(lab9.System1Strategy().select(context("Plan 5 days in Istanbul"))).name == "big"
