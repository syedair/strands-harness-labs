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


def test_jev_skipped_without_key(monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(showdown, "_kev_up", lambda: False)
    monkeypatch.setattr(showdown, "_laya_router", lambda: None)
    names = [name for name, _ in showdown.contenders()]
    assert names == ["qwen3.5 (stand-in)"]
    out = capsys.readouterr().out
    assert "TYPESAFE_API_KEY" in out and "Kev" in out and "laya" in out


def test_all_contenders_when_available(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    monkeypatch.setattr(showdown, "_kev_up", lambda: True)
    monkeypatch.setattr(showdown, "_laya_router", lambda: object())
    names = [name for name, _ in showdown.contenders()]
    assert names == ["jev (paid)", "kev-4b (open)", "laya (open)", "qwen3.5 (stand-in)"]
