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
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)  # no trained model on this machine
    reasons = {"jev": "Jev needs TYPESAFE_API_KEY", "kev": "Kev isn't running", "laya": "Laya isn't installed"}
    monkeypatch.setattr(showdown, "unavailable", lambda model: reasons.get(model))
    monkeypatch.setattr(showdown, "ensure_kev", lambda: False)  # a real Kev may be running on this machine
    names = [name for name, _ in showdown.contenders()]
    assert names == ["qwen3.5 (stand-in)"]
    out = capsys.readouterr().out
    assert "skip jev (paid): Jev needs TYPESAFE_API_KEY" in out
    assert "Kev" in out and "Laya" in out


def test_all_contenders_when_available(monkeypatch):
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)  # no trained model on this machine
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    names = [name for name, _ in showdown.contenders()]
    assert names == ["jev (paid)", "kev-4b (open)", "laya (open)", "qwen3.5 (stand-in)"]


def test_contender_asks_its_own_backend(monkeypatch):
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)  # no trained model on this machine
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    seen = []
    monkeypatch.setattr(showdown, "yes_no", lambda state, q, model=None: seen.append(model) or 0.5)
    for _, ask in showdown.contenders():
        ask("state", "Q?")
    assert seen == ["jev", "kev", "laya", "ollama/qwen3.5:4b"]


def test_verdict_names_the_best_and_anyone_worse_than_a_coin_flip():
    import lab10_system1_showdown as lab10

    rows = [("jev (paid)", 0.029), ("kev-4b (open)", 0.098), ("qwen3.5 (stand-in)", 0.341)]
    text = lab10.verdict(rows)
    assert "jev (paid)" in text.split("\n")[0]
    assert "qwen3.5 (stand-in)" in text and "coin flip" in text
    assert "worse than a coin flip" not in lab10.verdict(rows[:2])


def test_the_fine_tuned_contender_joins_only_once_it_exists(monkeypatch):
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)
    assert "laya-travel (fine-tuned)" not in [n for n, _ in showdown.contenders()]
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: True)
    assert [n for n, _ in showdown.contenders()][-1] == "laya-travel (fine-tuned)"
