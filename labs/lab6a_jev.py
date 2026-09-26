# Lab 6a: Jev — ask a small, fast model narrow questions. It answers with probabilities. Your code decides.
import os
import sys

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from common.show import show

load_dotenv()

# 1. What happened. This is what Jev looks at: the user's words, and what the assistant wants to do next.
conversation = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""

# 2. What we want to know. Three narrow questions, three kinds of answer.
questions = {
    "named_city": Noul(instructions="Did the user say which city they mean?"),  # yes/no   -> P(yes)
    "intent": Choice(  # pick one -> P for each option
        instructions="What does the user want?",
        criteria={"weather": "the current weather", "packing": "a packing list", "itinerary": "a trip plan"},
    ),
    "urgency": Score(  # rate -> P for each level, and a score
        instructions="How urgent is the request?",
        criteria=["not urgent", "today", "right now"],
    ),
}

# More conversations to try once the first one makes sense.
more = [
    """user: What's the weather in Paris?
assistant wants to call: web_fetch(url="https://wttr.in/Paris?format=3")""",
    "user: I'm flying to Istanbul tomorrow morning, what should I pack?",
    "user: Maybe plan a trip to Japan next year?",
]


def main() -> None:
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("Set TYPESAFE_API_KEY in .env (get one at https://typesafe.ai)")
        sys.exit(1)
    jev = TypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"])

    for state in [conversation, *more]:
        # 3. Ask. One call, three answers.
        answers = jev.system_one(model="jev-latest", state=state, questions=questions).answers
        show(state, questions, answers)

        # 4. Jev only observes. Plain Python decides.
        if answers["named_city"].noul < 0.5:
            print("  → ask which city\n")
        else:
            print(f"  → go: {answers['intent'].choice}\n")


if __name__ == "__main__":
    main()
