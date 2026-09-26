import pytest

from common import showdown


def test_score_perfect_predictions():
    brier, accuracy = showdown.score({"a": 1.0, "b": 0.0}, {"a": 1, "b": 0})
    assert brier == 0.0
    assert accuracy == 1.0


def test_score_counts_half_as_yes():
    brier, accuracy = showdown.score({"a": 0.5, "b": 0.5}, {"a": 1, "b": 0})
    assert brier == pytest.approx(0.25)
    assert accuracy == 0.5


def test_datasets_are_labelled_both_ways():
    for data in (showdown.BEACH, showdown.TOOL_CALLS):
        assert set(data.values()) == {0, 1}
    assert len(showdown.BEACH) == 44
    assert len(showdown.TOOL_CALLS) == 12


def test_unavailable_contenders_are_skipped_with_reason(monkeypatch, capsys):
    reasons = {"jev": "Jev needs TYPESAFE_API_KEY", "kev": "Kev isn't running", "laya": "Laya isn't installed"}
    monkeypatch.setattr(showdown, "unavailable", lambda model: reasons.get(model))
    names = [name for name, _ in showdown.contenders()]
    assert names == ["qwen3.5 (stand-in)"]
    out = capsys.readouterr().out
    assert "skip jev (paid): Jev needs TYPESAFE_API_KEY" in out
    assert "Kev" in out and "Laya" in out


def test_all_contenders_when_available(monkeypatch):
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    names = [name for name, _ in showdown.contenders()]
    assert names == ["jev (paid)", "kev-4b (open)", "laya (open)", "qwen3.5 (stand-in)"]


def test_contender_asks_its_own_backend(monkeypatch):
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    seen = []
    monkeypatch.setattr(showdown, "yes_no", lambda state, q, model=None: seen.append(model) or 0.5)
    for _, ask in showdown.contenders():
        ask("state", "Q?")
    assert seen == ["jev", "kev", "laya", "ollama/qwen3.5:4b"]
