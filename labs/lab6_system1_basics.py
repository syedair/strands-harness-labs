# Lab 6: System 1 basics — a small local model stands in for a System 1 model: typed questions in, probabilities out.
from common.config import SYSTEM1_MODEL
from common.system1 import check_system1, choice, yes_no, yes_no_many

CONVERSATION = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""


def main() -> None:
    check_system1()
    print(f"Classifier: {SYSTEM1_MODEL}\n\n{CONVERSATION}\n")

    # 1. One yes/no question -> one probability.
    p_city = yes_no(CONVERSATION, "Did the user say which city they mean?")
    print(f"P(user named a city) = {p_city:.2f}")

    # 2. Several narrow questions at once.
    for name, p in yes_no_many(
        CONVERSATION,
        {
            "args_grounded": "Are the tool's argument values based on what the user actually said?",
            "missing_info": "Is information missing that the tool needs?",
        },
    ).items():
        print(f"P({name}) = {p:.2f}")

    # 3. A choice -> a probability per option.
    intent = choice("user: Plan me 5 days in Istanbul under $1000", "What does the user want?",
                    ["weather", "packing list", "itinerary"])
    print("\nIntent:", {option: round(p, 2) for option, p in intent.items()})

    # 4. The classifier only observes. Plain Python decides.
    decision = "ask the user for the city" if p_city < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
