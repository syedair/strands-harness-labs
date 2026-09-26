# Lab 6e: standardized — the same questions through one helper. Switch models with SYSTEM1_MODEL in .env.
from common.config import SYSTEM1_MODEL
from common.system1 import check_system1, choice, yes_no_many

STATE = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""


def main() -> None:
    check_system1()
    print(f"System 1 model: {SYSTEM1_MODEL}   (try jev, kev, laya or ollama/qwen3.5:4b)\n{STATE}\n")

    # Yes/no questions -> one probability each. Labs 7-9 use exactly these helpers.
    p = yes_no_many(STATE, {
        "named_city": "Did the user say which city they mean?",
        "missing_info": "Is information missing that the tool needs?",
    })
    for name, value in p.items():
        print(f"P({name}) = {value:.2f}")

    # A choice -> a probability per option.
    intent = choice(STATE, "What does the user want?", ["weather", "packing list", "itinerary"])
    print("Intent:", {option: round(value, 2) for option, value in intent.items()})

    # The classifier only observes. Plain Python decides.
    decision = "ask the user for the city" if p["named_city"] < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
