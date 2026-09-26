import math
from types import SimpleNamespace

import pytest

from common import system1


def lp(p):
    return math.log(p)


def test_label_probabilities_sums_case_and_space_variants():
    top = [
        {"token": "no", "logprob": lp(0.70)},
        {"token": "yes", "logprob": lp(0.20)},
        {"token": "No", "logprob": lp(0.05)},
        {"token": " yes", "logprob": lp(0.05)},
    ]
    probs = system1.label_probabilities(top, ["yes", "no"])
    assert probs["yes"] == pytest.approx(0.25)
    assert probs["no"] == pytest.approx(0.75)


def test_label_probabilities_ignores_other_tokens_and_renormalizes():
    top = [{"token": "maybe", "logprob": lp(0.5)}, {"token": "yes", "logprob": lp(0.3)}, {"token": "no", "logprob": lp(0.1)}]
    probs = system1.label_probabilities(top, ["yes", "no"])
    assert probs["yes"] == pytest.approx(0.75)


def test_label_probabilities_missing_label_is_zero():
    probs = system1.label_probabilities([{"token": "yes", "logprob": lp(0.9)}], ["yes", "no"])
    assert probs == {"yes": 1.0, "no": 0.0}


def test_label_probabilities_no_labels_present_is_uniform():
    probs = system1.label_probabilities([{"token": "<think>", "logprob": lp(0.9)}], ["a", "b", "c"])
    assert probs == pytest.approx({"a": 1 / 3, "b": 1 / 3, "c": 1 / 3})


def fake_post(tokens, sent):
    def post(payload):
        sent.append(payload)
        return {"logprobs": [{"top_logprobs": [{"token": t, "logprob": lp(p)} for t, p in tokens]}]}

    return post


def test_yes_no_sends_single_token_no_thinking_request(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_post", fake_post([("yes", 0.8), ("no", 0.2)], sent))
    assert system1.yes_no("user: hi", "Is this a greeting?") == pytest.approx(0.8)
    payload = sent[0]
    assert payload["think"] is False
    assert payload["logprobs"] is True
    assert payload["options"]["num_predict"] == 1
    assert payload["options"]["temperature"] == 0


def test_choice_maps_letters_back_to_option_names(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_post", fake_post([("b", 0.6), ("A", 0.4)], sent))
    probs = system1.choice("text", "How hard?", ["easy", "hard"])
    assert probs == pytest.approx({"easy": 0.4, "hard": 0.6})
    assert "a) easy" in sent[0]["messages"][-1]["content"]


def test_yes_no_many_keeps_keys(monkeypatch):
    monkeypatch.setattr(system1, "_post", fake_post([("yes", 0.9), ("no", 0.1)], []))
    probs = system1.yes_no_many("state", {"grounded": "Q1?", "premature": "Q2?"})
    assert set(probs) == {"grounded", "premature"}


# --- choosing the backend: SYSTEM1_MODEL = ollama/<name> | jev | kev | laya ---

def fake_system_one(answers, sent):
    def post(url, payload, headers):
        sent.append((url, payload, headers))
        return {"answers": answers}

    return post


def test_jev_asks_all_questions_in_one_request(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    sent = []
    monkeypatch.setattr(system1, "_system_one_post",
                        fake_system_one({"a": {"noul": 0.9}, "b": {"noul": 0.2}}, sent))
    probs = system1.yes_no_many("state", {"a": "Q1?", "b": "Q2?"}, model="jev")
    assert probs == {"a": 0.9, "b": 0.2}
    assert len(sent) == 1
    url, payload, headers = sent[0]
    assert url == "https://api.typesafe.ai/v1/systemone"
    assert payload["questions"]["a"] == {"type": "noul", "instructions": "Q1?"}
    assert headers == {"Authorization": "Bearer k"}


def test_kev_uses_local_server_without_key(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_system_one_post", fake_system_one({"q": {"noul": 0.7}}, sent))
    assert system1.yes_no("state", "Q?", model="kev") == pytest.approx(0.7)
    url, payload, headers = sent[0]
    assert url.endswith("/v1/systemone") and payload["model"] == "kev-latest" and headers is None


def test_choice_via_system_one_returns_option_probabilities(monkeypatch):
    sent = []
    answers = {"q": {"choice": "hard", "probabilities": {"easy": 0.3, "hard": 0.7}}}
    monkeypatch.setattr(system1, "_system_one_post", fake_system_one(answers, sent))
    assert system1.choice("s", "How hard?", ["easy", "hard"], model="kev") == {"easy": 0.3, "hard": 0.7}
    assert sent[0][1]["questions"]["q"]["criteria"] == {"easy": "easy", "hard": "hard"}


def test_laya_uses_its_router(monkeypatch):
    class FakeRouter:
        def predict(self, state, questions):
            return {"answers": {key: {"noul": 0.4} for key in questions}}

    monkeypatch.setattr(system1, "_laya_router", lambda: FakeRouter())
    assert system1.yes_no("s", "Q?", model="laya") == pytest.approx(0.4)


def test_bare_ollama_name_still_works(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_post", fake_post([("yes", 1.0)], sent))
    system1.yes_no("s", "Q?", model="qwen3.5:9b")
    assert sent[0]["model"] == "qwen3.5:9b"


def test_unavailable_reasons(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1, "_laya_router", lambda: None)
    monkeypatch.setattr(system1.config, "_pulled_models", lambda: {"qwen3.5:4b"})
    assert "TYPESAFE_API_KEY" in system1.unavailable("jev")
    assert "Kev" in system1.unavailable("kev")
    assert "--extra laya" in system1.unavailable("laya")
    assert "ollama pull qwen3.5:9b" in system1.unavailable("ollama/qwen3.5:9b")
    assert system1.unavailable("ollama/qwen3.5:4b") is None


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="ollama/<name>, jev, kev or laya"):
        system1.yes_no("s", "Q?", model="gpt")


# --- ensure_kev: offer to start Kev in the background, once ---

class FakeStdin:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


def test_ensure_kev_does_nothing_when_running(monkeypatch):
    monkeypatch.setattr(system1, "_kev_up", lambda: True)
    monkeypatch.setattr(system1.subprocess, "run", lambda *a, **k: pytest.fail("should not start Kev"))
    assert system1.ensure_kev() is True


def test_ensure_kev_prints_command_without_a_terminal(monkeypatch, capsys):
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1.sys, "stdin", FakeStdin(tty=False))
    assert system1.ensure_kev() is False
    assert "./kev.sh start" in capsys.readouterr().out


def test_ensure_kev_starts_it_when_user_agrees(monkeypatch):
    started = []
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1.sys, "stdin", FakeStdin(tty=True))
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr(system1.subprocess, "run",
                        lambda cmd, **k: started.append(cmd) or SimpleNamespace(returncode=0))
    assert system1.ensure_kev() is True
    assert started[0][-2:] == [str(system1.KEV_SCRIPT), "start"]


def test_ensure_kev_respects_no(monkeypatch):
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1.sys, "stdin", FakeStdin(tty=True))
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    monkeypatch.setattr(system1.subprocess, "run", lambda *a, **k: pytest.fail("should not start Kev"))
    assert system1.ensure_kev() is False


def test_check_system1_offers_kev(monkeypatch):
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1, "ensure_kev", lambda: True)
    system1.check_system1("kev")  # no exit: Kev was started


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
def test_ensure_kev_treats_no_answer_as_no(monkeypatch, capsys, error):
    monkeypatch.setattr(system1, "_kev_up", lambda: False)
    monkeypatch.setattr(system1.sys, "stdin", FakeStdin(tty=True))

    def no_answer(prompt):
        raise error

    monkeypatch.setattr("builtins.input", no_answer)
    assert system1.ensure_kev() is False
    assert "./kev.sh start" in capsys.readouterr().out


def test_laya_answers_one_caller_at_a_time(monkeypatch):
    """Laya runs on the Mac's GPU in-process; two threads at once crash Metal, so calls must queue."""
    import threading
    import time
    from common import system1

    inside, most = [0], [0]

    class FakeRouter:
        def predict(self, state, questions):
            inside[0] += 1
            most[0] = max(most[0], inside[0])
            time.sleep(0.05)
            inside[0] -= 1
            return {"answers": {k: {"noul": 0.5} for k in questions}}

    monkeypatch.setattr(system1, "_laya_router", lambda: FakeRouter())
    threads = [threading.Thread(target=system1.yes_no_many, args=("s", {"q": "?"}, "laya")) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert most[0] == 1
