# Lab 10: System 1 showdown — Jev vs Kev vs Laya vs our Qwen stand-in, on labelled questions.
import time

from common.showdown import BEACH, TOOL_CALLS, contenders, score

ROUNDS = [
    ("Beach destinations", BEACH, "Is this primarily a beach or tropical holiday destination?"),
    # The same tool calls, asked two ways:
    ("Tool calls, abstract question", TOOL_CALLS,
     "Are the tool's argument values based on facts the user actually provided?"),
    ("Tool calls, concrete question", TOOL_CALLS,
     "Did the user mention the same city that the tool call uses?"),
]


def main() -> None:
    players = contenders()

    for title, labels, question in ROUNDS:
        print(f"\n=== {title} ({len(labels)} labelled) ===\nQ: {question}")
        print(f"{'model':20}{'brier':>7}{'acc':>6}{'ms':>6}")
        for name, ask in players:
            ask(next(iter(labels)), question)  # warm-up: model load / connection, not timed
            start = time.perf_counter()
            probs = {state: ask(state, question) for state in labels}
            ms = (time.perf_counter() - start) / len(labels) * 1000
            brier, accuracy = score(probs, labels)
            print(f"{name:20}{brier:7.3f}{accuracy:6.0%}{ms:6.0f}")

    print("\nBrier: lower is better (0 = perfect, 0.25 = coin flip).")


if __name__ == "__main__":
    main()
