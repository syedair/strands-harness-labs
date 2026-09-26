# Lab 6b: Kev — an open Jev-alike on your own machine. Same SDK, same questions: only the URL changes.
import sys

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

load_dotenv()
from common.config import KEV_URL  # noqa: E402  (http://127.0.0.1:8009 by default)
from common.system1 import ensure_kev  # noqa: E402

STATE = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""

QUESTIONS = {
    # Noul: a yes/no question -> the probability that it's true
    "named_city": Noul(instructions="Did the user say which city they mean?"),
    # Choice: pick one option -> a probability for each
    "intent": Choice(
        instructions="What does the user want?",
        criteria={"weather": "the current weather", "packing": "a packing list", "itinerary": "a trip plan"},
    ),
    # Score: rate on your scale -> a probability-weighted value
    "urgency": Score(instructions="How urgent is the request?", criteria=["not urgent", "today", "right now"]),
}


def main() -> None:
    if not ensure_kev():  # Kev is a local server: offers to start it in the background
        sys.exit(1)

    kev = TypeSafeClient(base_url=KEV_URL, api_key="local")  # NEW: your machine, no real key
    answers = kev.system_one(model="kev-latest", state=STATE, questions=QUESTIONS).answers

    print(f"{STATE}\n")
    print(f"P(user named a city) = {answers['named_city'].noul:.2f}")
    intent = answers["intent"]
    print(f"Intent: {intent.choice}  {({k: round(v, 2) for k, v in intent.probabilities.items()})}")
    print(f"Urgency (0-2): {answers['urgency'].score:.2f}")

    # Kev only observes. Plain Python decides.
    decision = "ask the user for the city" if answers["named_city"].noul < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
