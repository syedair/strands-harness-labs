# Lab 10 helpers: labelled travel questions and four System 1 contenders.
from functools import partial

from common.system1 import unavailable, yes_no

# 1 = primarily a beach / tropical getaway. From the systemone-model-typesafeai demo.
BEACH = {
    "Malé (Maldives)": 1, "Denpasar (Bali)": 1, "Phuket": 1, "Cancún": 1, "Goa": 1,
    "Zanzibar": 1, "Mahé (Seychelles)": 1, "Port Louis (Mauritius)": 1, "Phu Quoc": 1,
    "Nadi (Fiji)": 1, "Honolulu": 1, "Miami": 1, "Cartagena": 1, "Rio de Janeiro": 1, "Nice": 1,
    "Zurich": 0, "Frankfurt": 0, "Geneva": 0, "Munich": 0, "Vienna": 0, "Prague": 0,
    "Moscow": 0, "Aspen": 0, "Zermatt": 0, "Chamonix": 0, "Innsbruck": 0, "Kyoto": 0,
    "Tokyo": 0, "Beijing": 0, "Seoul": 0, "New York": 0, "Chicago": 0, "Toronto": 0,
    "London": 0, "Paris": 0, "Kathmandu": 0, "Reykjavik": 0, "Baku": 0, "Tashkent": 0,
    # coastal cities that are NOT primarily beach trips — the hard middle
    "Singapore": 0, "Barcelona": 0, "Sydney": 0, "Cape Town": 0, "Lisbon": 0,
}


def _call(user: str, city: str) -> str:
    return f'user: {user}\n\nProposed tool call: web_fetch(url="https://wttr.in/{city}?format=3")'


# 1 = the city in the tool call came from the user (lab 7's question).
TOOL_CALLS = {
    _call("What's the weather in Paris?", "Paris"): 1,
    _call("I'm flying to Rome tomorrow, how's the weather there?", "Rome"): 1,
    _call("Is it raining in London right now?", "London"): 1,
    _call("Weather for Tokyo please", "Tokyo"): 1,
    _call("I live in Dubai. What's it like at home today?", "Dubai"): 1,
    _call("Should I take a jacket to Istanbul?", "Istanbul"): 1,
    _call("What's the weather?", "Seattle"): 0,
    _call("Is it going to rain today?", "London"): 0,
    _call("What should I pack for my trip?", "Istanbul"): 0,
    _call("How hot is it?", "Dubai"): 0,
    _call("What's the weather in Paris?", "Berlin"): 0,
    _call("Do I need an umbrella this weekend?", "Seattle"): 0,
}


def score(probs: dict[str, float], labels: dict[str, int]) -> tuple[float, float]:
    """Brier score (lower is better) and accuracy at a 0.5 threshold."""
    brier = sum((probs[k] - y) ** 2 for k, y in labels.items()) / len(labels)
    accuracy = sum((probs[k] >= 0.5) == bool(y) for k, y in labels.items()) / len(labels)
    return brier, accuracy


CONTENDERS = [
    ("jev (paid)", "jev"),
    ("kev-4b (open)", "kev"),
    ("laya (open)", "laya"),
    ("qwen3.5 (stand-in)", "ollama/qwen3.5:4b"),
]


def contenders() -> list[tuple[str, object]]:
    """Every contender that can run here; the rest are skipped with the fix."""
    found = []
    for name, model in CONTENDERS:
        problem = unavailable(model)
        if problem:
            print(f"skip {name}: {problem}")
        else:
            found.append((name, partial(yes_no, model=model)))
    return found
