# Lab 6c: Laya — an open System 1 model from a different family (BERT-based). Same question shapes.
import os
import sys
import warnings

from common.show import pause, show
from lab6a_jev import conversation, more  # the same conversations as lab 6a

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")  # quiet the model download check
# Laya warns that its confidence values are uncalibrated; we only use the probabilities.
warnings.filterwarnings("ignore", message="laya: this checkpoint")

try:
    from laya import Router
except ImportError:
    print("Laya isn't installed. Run: uv sync --extra laya --inexact")
    sys.exit(1)

# The same three questions as lab 6a, written as plain dicts.
questions = {
    "named_city": {"type": "noul", "instructions": "Did the user say which city they mean?"},  # yes/no
    "intent": {  # pick one
        "type": "choice",
        "instructions": "What does the user want?",
        "criteria": {"weather": "the current weather", "packing": "a packing list", "itinerary": "a trip plan"},
    },
    "urgency": {  # rate
        "type": "score",
        "instructions": "How urgent is the request?",
        "criteria": ["not urgent", "today", "right now"],
    },
}


def main() -> None:
    laya = Router()  # NEW: downloads the model on first run, then runs on your machine

    for state in [conversation, *more]:
        pause(state)  # show the conversation, then wait for Enter

        # Ask. One forward pass, three answers.
        answers = laya.predict(state, questions)["answers"]
        show(state, questions, answers, header=False)

        # Laya only observes. Plain Python decides.
        if answers["named_city"]["noul"] < 0.5:
            print("  → ask which city\n")
        else:
            print(f"  → go: {answers['intent']['choice']}\n")


if __name__ == "__main__":
    main()
