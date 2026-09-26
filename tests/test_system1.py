import math

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
