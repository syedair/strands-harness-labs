# Lab 6c: Laya — an open System 1 model from a different family (BERT-based). Same question shapes.
import sys

from common.travel_cases import CASES, short

try:
    from laya import Router
except ImportError:
    print("Laya isn't installed. Run: uv sync --extra laya --inexact")
    sys.exit(1)

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

    print(f"{'user said':44}{'P(city)':>8}  {'intent':10}{'urgency 0-2':>12}  decision")
    for case in CASES:
        answers = laya.predict(case, QUESTIONS)["answers"]  # one forward pass
        p_city, intent, urgency = answers["named_city"]["noul"], answers["intent"]["choice"], answers["urgency"]["score"]

        # Laya only observes. Plain Python decides.
        decision = "ask which city" if p_city < 0.5 else f"go: {intent}"
        print(f"{short(case):44}{p_city:8.2f}  {intent:10}{urgency:12.2f}  {decision}")


if __name__ == "__main__":
    main()
