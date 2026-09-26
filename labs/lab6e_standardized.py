# Lab 6e: standardized — the same questions through one helper. Switch models with SYSTEM1_MODEL in .env.
from common.config import SYSTEM1_MODEL
from common.show import pause, show
from common.system1 import check_system1, choice, yes_no
from lab6a_jev import conversation, more  # the same conversations as lab 6a

# Two question shapes every System 1 model here can answer. Labs 7-9 use exactly these two helpers.
questions = {
    "named_city": {"type": "noul", "instructions": "Did the user say which city they mean?"},  # yes/no
    "intent": {"type": "choice", "instructions": "What does the user want?",  # pick one
               "criteria": ["weather", "packing list", "itinerary"]},
}


def main() -> None:
    check_system1()
    print(f"System 1 model: {SYSTEM1_MODEL}   (try jev, kev, laya or ollama/qwen3.5:4b)\n")

    for state in [conversation, *more]:
        pause(state)  # show the conversation, then wait for Enter

        # Ask. The same two helpers, whichever model answers.
        p_city = yes_no(state, questions["named_city"]["instructions"])
        probs = choice(state, questions["intent"]["instructions"], questions["intent"]["criteria"])
        intent = max(probs, key=probs.get)
        answers = {"named_city": {"type": "noul", "noul": p_city},
                   "intent": {"type": "choice", "choice": intent, "probabilities": probs}}
        show(state, questions, answers, header=False)

        # The classifier only observes. Plain Python decides.
        if p_city < 0.5:
            print("  → ask which city\n")
        else:
            print(f"  → go: {intent}\n")


if __name__ == "__main__":
    main()
