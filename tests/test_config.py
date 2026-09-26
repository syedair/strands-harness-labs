import pytest

from common import config


def test_check_ollama_exits_with_pull_hint_when_model_missing(monkeypatch, capsys):
    monkeypatch.setattr(config, "_pulled_models", lambda: {"gpt-oss:20b"})
    with pytest.raises(SystemExit) as exit_info:
        config.check_ollama("gpt-oss:20b", "qwen3.5:4b")
    assert exit_info.value.code == 1
    assert "ollama pull qwen3.5:4b" in capsys.readouterr().out


def test_check_ollama_exits_with_serve_hint_when_ollama_down(monkeypatch, capsys):
    def down():
        raise config.httpx.ConnectError("refused")

    monkeypatch.setattr(config, "_pulled_models", down)
    with pytest.raises(SystemExit):
        config.check_ollama("qwen3.5:4b")
    assert "ollama serve" in capsys.readouterr().out


def test_check_ollama_accepts_latest_tag(monkeypatch):
    monkeypatch.setattr(config, "_pulled_models", lambda: {"qwen3.5:4b"})
    config.check_ollama("qwen3.5:4b")  # no exit


def test_check_ollama_ignores_non_ollama_main_model(monkeypatch):
    monkeypatch.setattr(config, "_pulled_models", lambda: set())
    config.check_ollama("bedrock/us.anthropic.claude-sonnet-5")  # no exit
