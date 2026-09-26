# Lab 6e: standardized — the same questions through one helper. Switch models with SYSTEM1_MODEL in .env.
from common.config import SYSTEM1_MODEL
from common.system1 import check_system1, choice, yes_no
from common.travel_cases import CASES, short


def main() -> None:
    check_system1()
    print(f"System 1 model: {SYSTEM1_MODEL}   (try jev, kev, laya or ollama/qwen3.5:4b)\n")

    print(f"{'user said':44}{'P(city)':>8}  {'intent':14}decision")
    for case in CASES:
        # Labs 7-9 use exactly these two helpers.
        p_city = yes_no(case, "Did the user say which city they mean?")
        probs = choice(case, "What does the user want?", ["weather", "packing list", "itinerary"])
        intent = max(probs, key=probs.get)

        # The classifier only observes. Plain Python decides.
        decision = "ask which city" if p_city < 0.5 else f"go: {intent}"
        print(f"{short(case):44}{p_city:8.2f}  {intent:14}{decision}")


if __name__ == "__main__":
    main()
