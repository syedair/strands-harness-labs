# tests/test_travel_data.py
import json
import re

from common import travel_data
from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS

HELD_OUT_CITIES = {m for s in TOOL_CALLS for m in re.findall(r"wttr\.in/(\w+)", s)}


def test_training_questions_share_nothing_with_lab_10():
    pairs = travel_data.training_questions()
    states = {s for s, _ in pairs}
    assert not states & set(BEACH) and not states & set(TOOL_CALLS)
    for state, question in pairs:
        if question != BEACH_Q:
            assert re.search(r"wttr\.in/(\w+)", state).group(1) not in HELD_OUT_CITIES


def test_every_tool_call_is_asked_both_ways_and_covers_all_three_kinds():
    pairs = travel_data.training_questions()
    lab10_format = lambda s: "web_fetch(url=" in s
    calls = [s for s, q in pairs if q == ABSTRACT_Q]
    assert sorted(calls) == sorted(s for s, q in pairs if q == CONCRETE_Q and lab10_format(s))
    kinds = set()
    for call in calls:
        user, city = re.match(r"user: (.*)\n\nProposed tool call: .*wttr\.in/(\w+)", call).groups()
        named = [c for c in travel_data.CITIES if c in user]
        kinds.add("given" if city in named else "different" if named else "none")
    assert kinds == {"given", "different", "none"}


def test_label_asks_the_teacher_and_caches(tmp_path):
    asked = []
    ask = lambda state, question, model=None: asked.append(model) or 0.25
    pairs = [("Boracay", BEACH_Q), ("Madrid", BEACH_Q)]
    rows = travel_data.label(pairs, "kev", tmp_path / "labels.json", ask=ask)
    assert rows == [{"state": "Boracay", "question": BEACH_Q, "p": 0.25},
                    {"state": "Madrid", "question": BEACH_Q, "p": 0.25}]
    assert asked == ["kev", "kev"]
    again = travel_data.label(pairs, "kev", tmp_path / "labels.json", ask=lambda *a, **k: 1 / 0)
    assert again == rows  # cached: the teacher isn't asked again


def test_label_cache_is_rebuilt_when_questions_or_teacher_change(tmp_path):
    cache = tmp_path / "labels.json"
    travel_data.label([("Boracay", BEACH_Q)], "kev", cache, ask=lambda *a, **k: 0.9)
    rows = travel_data.label([("Madrid", BEACH_Q)], "kev", cache, ask=lambda *a, **k: 0.1)
    assert rows[0]["state"] == "Madrid" and rows[0]["p"] == 0.1
    rows = travel_data.label([("Madrid", BEACH_Q)], "jev", cache, ask=lambda *a, **k: 0.2)
    assert rows[0]["p"] == 0.2 and json.loads(cache.read_text())["teacher"] == "jev"


def test_no_training_place_is_part_of_a_held_out_one():
    # Waikiki is in Honolulu and Copacabana in Rio de Janeiro, both in lab 10's beach round
    assert not {"Waikiki", "Copacabana"} & set(travel_data.PLACES)


def test_lab_7s_gate_questions_are_trained_in_lab_7s_own_format():
    import lab7_tool_call_gate as lab7

    pairs = travel_data.training_questions()
    gate_format = r'user: .+\n\nProposed tool call: web_fetch\(\{"url": "https://wttr\.in/\w+\?format=3"\}\)'
    for key, question in lab7.QUESTIONS.items():
        states = [s for s, q in pairs if q == question and re.fullmatch(gate_format, s)]
        assert len(states) == 300, key  # what before_tool_call shows System 1
        assert not {re.search(r"wttr\.in/(\w+)", s).group(1) for s in states} & HELD_OUT_CITIES


REPO_LABELS = travel_data.REPO_LABELS


def test_the_labels_in_the_repo_match_the_training_questions():
    saved = json.loads(REPO_LABELS.read_text())
    assert saved["teacher"] == "kev"
    assert [(r["state"], r["question"]) for r in saved["rows"]] == travel_data.training_questions()
    assert all(0 <= r["p"] <= 1 for r in saved["rows"])


def test_without_a_teacher_the_repo_labels_are_used(tmp_path):
    pairs = travel_data.training_questions()
    rows, source = travel_data.labels_for(pairs, "kev", tmp_path / "labels.json", teacher_ready=False,
                                          ask=lambda *a, **k: 1 / 0)
    assert source == "repo" and len(rows) == len(pairs)


def test_with_a_teacher_it_labels_live(tmp_path):
    pairs = [("Boracay", BEACH_Q)]
    rows, source = travel_data.labels_for(pairs, "kev", tmp_path / "labels.json", teacher_ready=True,
                                          ask=lambda *a, **k: 0.9)
    assert source == "teacher" and rows[0]["p"] == 0.9


def test_examples_show_a_yes_a_no_and_a_borderline_label_per_question():
    rows = [{"state": f"s{i}", "question": q, "p": p} for q in ("Q1", "Q2")
            for i, p in enumerate([0.02, 0.48, 0.55, 0.97, 0.7])]
    picked = travel_data.examples(rows, ["Q1", "Q2"])
    assert [r["p"] for r in picked] == [0.97, 0.02, 0.48, 0.97, 0.02, 0.48]
