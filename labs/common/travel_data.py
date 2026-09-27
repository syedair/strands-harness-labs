# Lab 10b's training data: travel questions that share nothing with lab 10's held-out sets, labelled by a teacher.
import itertools
import json
import random
from pathlib import Path

from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS, _call
from common.system1 import yes_no

# New destinations for the beach question: beach getaways, inland and mountain cities, coastal cities.
PLACES = [
    "Boracay", "Langkawi", "Koh Samui", "Krabi", "Bora Bora", "Tahiti", "Aruba", "Barbados", "Punta Cana",
    "Montego Bay", "Nassau", "Tulum", "Playa del Carmen", "Cabo San Lucas", "Maui", "Gold Coast",
    "Byron Bay", "Cairns", "Mykonos", "Santorini", "Ibiza", "Mallorca", "Tenerife", "Gran Canaria", "Crete",
    "Rhodes", "Antalya", "Bodrum", "Hurghada", "Sharm El Sheikh", "Mombasa", "Diani Beach", "Praslin", "Lombok",
    "Gili Islands", "Palawan", "Cebu", "Nha Trang", "Da Nang", "Mirissa", "Varkala", "Andaman Islands",
    "Fort Lauderdale", "Key West", "San Juan", "Curaçao", "St Lucia", "Antigua", "Florianópolis",
    "Salvador de Bahia", "Punta del Este", "Jeffreys Bay", "Zakynthos", "Sardinia", "Corsica",
    "Lagos (Algarve)", "Madrid", "Budapest", "Warsaw", "Krakow", "Brussels", "Amsterdam", "Stockholm", "Oslo",
    "Helsinki", "Copenhagen", "Dublin", "Edinburgh", "Florence", "Milan", "Salzburg", "Bern", "Lucerne",
    "Interlaken", "St. Moritz", "Banff", "Whistler", "Denver", "Salt Lake City", "Las Vegas", "Phoenix",
    "Mexico City", "Bogotá", "Quito", "La Paz", "Cusco", "Santiago", "Buenos Aires", "Marrakech", "Cairo",
    "Nairobi", "Addis Ababa", "Johannesburg", "Delhi", "Jaipur", "Agra", "Varanasi", "Lhasa", "Ulaanbaatar",
    "Almaty", "Tbilisi", "Yerevan", "Tehran", "Riyadh", "Amman", "Jerusalem", "Xi'an", "Chengdu", "Shanghai",
    "Osaka", "Sapporo", "Busan", "Taipei", "Hong Kong", "Hanoi", "Bangkok", "Kuala Lumpur", "Jakarta", "Manila",
    "Mumbai", "Chennai", "Kolkata", "Athens", "Naples", "Venice", "Genoa", "Marseille", "Bordeaux", "Porto",
    "Valencia", "Seville", "Hamburg", "Gdansk", "Tallinn", "Riga", "Vilnius", "St. Petersburg", "Vladivostok",
    "Vancouver", "San Francisco", "Los Angeles", "Boston", "Montreal", "Quebec City", "Halifax", "Auckland",
    "Wellington", "Melbourne", "Perth", "Hobart", "Dakar", "Accra", "Casablanca", "Tunis", "Alexandria",
]

# Tool calls: cities that never appear in lab 10's held-out tool calls.
CITIES = ["Madrid", "Riga", "Oslo", "Lima", "Cairo", "Delhi", "Bangkok", "Sydney", "Toronto", "Athens",
          "Vienna", "Lisbon", "Nairobi", "Seoul", "Denver", "Dublin", "Hanoi", "Doha", "Milan", "Porto"]
WITH_CITY = ["What's the weather in {c}?", "How's the weather in {c} today?", "Is it cold in {c}?",
             "I'm heading to {c} next week, what's it like there?", "Forecast for {c} please",
             "Do I need a coat in {c}?", "I live in {c}. Is it raining at home?", "Is {c} sunny right now?",
             "Flying to {c} tomorrow. Will it rain?", "What should I wear in {c} this weekend?"]
NO_CITY = ["What's it like outside?", "Will it rain later?", "Do I need sunscreen today?", "How cold is it?",
           "What's the forecast for tomorrow?", "Should I bring an umbrella?", "Is it windy today?",
           "What should I wear today?", "Any storms coming?", "What's the temperature right now?"]


def _messages_and_cities(seed: int = 7, n: int = 300) -> list[tuple[str, str]]:
    """(what the user said, the city the tool call uses): the city was given, a different one, or never mentioned."""
    rng = random.Random(seed)
    found = set()
    for tpl, city in itertools.product(WITH_CITY, CITIES):
        found.add((tpl.format(c=city), city))  # the user's city
        found.add((tpl.format(c=city), rng.choice([c for c in CITIES if c != city])))  # a different one
    for tpl in NO_CITY:
        for city in rng.sample(CITIES, 6):
            found.add((tpl, city))  # no city given: a guess
    held_out = set(TOOL_CALLS)
    return rng.sample(sorted(p for p in found if _call(*p) not in held_out), n)


def tool_calls(seed: int = 7, n: int = 300) -> list[str]:
    """The tool calls in lab 10's format."""
    return [_call(user, city) for user, city in _messages_and_cities(seed, n)]


def gate_calls(seed: int = 7, n: int = 300) -> list[str]:
    """The same tool calls in lab 7's format: what its gate shows System 1 before a tool runs."""
    return [f"user: {user}\n\nProposed tool call: web_fetch({json.dumps({'url': f'https://wttr.in/{city}?format=3'})})"
            for user, city in _messages_and_cities(seed, n)]


def training_questions(seed: int = 7, n_calls: int = 300) -> list[tuple[str, str]]:
    """(state, question) pairs: every new destination asked the beach question, every tool call asked lab 10's two
    questions, and lab 7's gate questions in the gate's own format (so SYSTEM1_MODEL=laya-travel can run lab 7)."""
    from lab7_tool_call_gate import QUESTIONS as GATE  # the four questions lab 7's gate asks

    places = [p for p in PLACES if p not in BEACH]
    return ([(p, BEACH_Q) for p in places]
            + [(s, q) for s in tool_calls(seed, n_calls) for q in (ABSTRACT_Q, CONCRETE_Q)]
            + [(s, q) for s in gate_calls(seed, n_calls) for q in GATE.values()])


def label(pairs: list[tuple[str, str]], teacher: str, cache: Path, ask=yes_no) -> list[dict]:
    """The teacher's probability for each question. Cached: the same questions and teacher skip the teacher."""
    wanted = [[s, q] for s, q in pairs]
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved["teacher"] == teacher and [[r["state"], r["question"]] for r in saved["rows"]] == wanted:
            return saved["rows"]
    rows = [{"state": s, "question": q, "p": ask(s, q, model=teacher)} for s, q in pairs]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"teacher": teacher, "rows": rows}, indent=1))
    return rows
