# Lab 6c: Laya — an open System 1 model from a different family (BERT-based). Same question shapes.
import sys

try:
    from laya import Router
except ImportError:
    print("Laya isn't installed. Run: uv sync --extra laya")
    sys.exit(1)

STATE = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""

# The same three questions as lab 6a, written as plain dicts.
QUESTIONS = {
    "named_city": {"type": "noul", "instructions": "Did the user say which city they mean?"},
    "intent": {
        "type": "choice",
        "instructions": "What does the user want?",
        "criteria": {"weather": "the current weather", "packing": "a packing list", "itinerary": "a trip plan"},
    },
    "urgency": {"type": "score", "instructions": "How urgent is the request?",
                "criteria": ["not urgent", "today", "right now"]},
}


def main() -> None:
    laya = Router()  # downloads the model on first run, then runs on your machine
    answers = laya.predict(STATE, QUESTIONS)["answers"]  # one forward pass

    print(f"{STATE}\n")
    print(f"P(user named a city) = {answers['named_city']['noul']:.2f}")
    intent = answers["intent"]
    print(f"Intent: {intent['choice']}  {({k: round(v, 2) for k, v in intent['probabilities'].items()})}")
    print(f"Urgency (0-2): {answers['urgency']['score']:.2f}")

    # Laya only observes. Plain Python decides.
    decision = "ask the user for the city" if answers["named_city"]["noul"] < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
