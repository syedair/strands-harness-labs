# Lab 6b: Kev — an open Jev-alike on your own machine. Same SDK, same questions: only the URL changes.
import sys

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from common.config import KEV_URL
from common.system1 import ensure_kev
from common.travel_cases import CASES, short

load_dotenv()

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

    print(f"{'user said':44}{'P(city)':>8}  {'intent':10}{'urgency 0-2':>12}  decision")
    for case in CASES:
        answers = kev.system_one(model="kev-latest", state=case, questions=QUESTIONS).answers
        p_city, intent, urgency = answers["named_city"].noul, answers["intent"].choice, answers["urgency"].score

        # Kev only observes. Plain Python decides.
        decision = "ask which city" if p_city < 0.5 else f"go: {intent}"
        print(f"{short(case):44}{p_city:8.2f}  {intent:10}{urgency:12.2f}  {decision}")


if __name__ == "__main__":
    main()
