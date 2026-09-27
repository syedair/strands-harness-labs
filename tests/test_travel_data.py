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
    calls = [s for s, q in pairs if q == ABSTRACT_Q]
    assert sorted(calls) == sorted(s for s, q in pairs if q == CONCRETE_Q)
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
