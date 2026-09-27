# Lab 6b: Kev — an open Jev-alike on your own machine. Same SDK, same questions: only the client changes.
import sys

from common.config import KEV_URL
from common.show import pause, show
from common.system1 import ensure_kev
from lab6a_jev import (  # the same conversations and questions as lab 6a
    conversation,
    more,
    questions,
)
from typesafe_sdk import TypeSafeClient


def main() -> None:
    if not ensure_kev():  # Kev is a local server: offers to start it in the background
        sys.exit(1)
    kev = TypeSafeClient(base_url=KEV_URL, api_key="local")  # NEW: your machine, no real key

    for state in [conversation, *more]:
        pause(state)  # show the conversation, then wait for Enter

        # Ask. One call, three answers.
        answers = kev.system_one(model="kev-latest", state=state, questions=questions).answers
        show(state, questions, answers, header=False)

        # Kev only observes. Plain Python decides.
        if answers["named_city"].noul < 0.5:
            print("  → ask which city\n")
        else:
            print(f"  → go: {answers['intent'].choice}\n")


if __name__ == "__main__":
    main()
