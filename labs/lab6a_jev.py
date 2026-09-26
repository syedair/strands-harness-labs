# Lab 6a: Jev — a System 1 model answers typed questions with probabilities. Your code decides.
import os
import sys

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

load_dotenv()

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
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("Set TYPESAFE_API_KEY in .env (get one at https://typesafe.ai)")
        sys.exit(1)

    jev = TypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"])
    answers = jev.system_one(model="jev-latest", state=STATE, questions=QUESTIONS).answers  # one call

    print(f"{STATE}\n")
    print(f"P(user named a city) = {answers['named_city'].noul:.2f}")
    intent = answers["intent"]
    print(f"Intent: {intent.choice}  {({k: round(v, 2) for k, v in intent.probabilities.items()})}")
    print(f"Urgency (0-2): {answers['urgency'].score:.2f}")

    # Jev only observes. Plain Python decides.
    decision = "ask the user for the city" if answers["named_city"].noul < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
