# Four example conversations for lab 6: watch the probabilities move from one to the next.
CASES = [
    # the model GUESSED the city — lab 7 catches exactly this
    'user: What\'s the weather?\nassistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")',
    'user: What\'s the weather in Paris?\nassistant wants to call: web_fetch(url="https://wttr.in/Paris?format=3")',
    "user: I'm flying to Istanbul tomorrow morning, what should I pack?",
    "user: Maybe plan a trip to Japan next year?",
]


def short(case: str) -> str:
    """The user's words, shortened for one table row."""
    words = case.splitlines()[0].removeprefix("user: ")
    return words if len(words) <= 42 else words[:41] + "…"
