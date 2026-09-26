# Lab 6a: Jev — a System 1 model answers typed questions with probabilities. Your code decides.
import os
import sys

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

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
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("Set TYPESAFE_API_KEY in .env (get one at https://typesafe.ai)")
        sys.exit(1)
    jev = TypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"])

    print(f"{'user said':44}{'P(city)':>8}  {'intent':10}{'urgency 0-2':>12}  decision")
    for case in CASES:
        answers = jev.system_one(model="jev-latest", state=case, questions=QUESTIONS).answers  # one call
        p_city, intent, urgency = answers["named_city"].noul, answers["intent"].choice, answers["urgency"].score

        # Jev only observes. Plain Python decides.
        decision = "ask which city" if p_city < 0.5 else f"go: {intent}"
        print(f"{short(case):44}{p_city:8.2f}  {intent:10}{urgency:12.2f}  {decision}")


if __name__ == "__main__":
    main()
