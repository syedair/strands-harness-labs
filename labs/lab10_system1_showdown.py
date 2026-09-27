# Lab 10: System 1 showdown — Jev vs Kev vs Laya vs our Qwen stand-in, on labelled questions.
#
# How we score a classifier: the Brier score. For every labelled example, take the probability the model gave,
# subtract the true answer (1 = yes, 0 = no), square it, and average. 0 is perfect; 0.25 is what you'd get by
# always answering 0.5 (a coin flip); above that is worse than guessing. Unlike accuracy, it punishes being
# confidently wrong, and that matters because our code acts on thresholds like 0.65.
import time

from common.show import COIN_FLIP, brier_row, wait
from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS, contenders, score

ROUNDS = [
    ("Beach destinations", BEACH, BEACH_Q),
    # The same tool calls, asked two ways: small models need concrete questions.
    ("Tool calls, abstract question", TOOL_CALLS, ABSTRACT_Q),
    ("Tool calls, concrete question", TOOL_CALLS, CONCRETE_Q),
]


def verdict(rows: list[tuple[str, float]]) -> str:
    """One plain sentence per round: who did best, and who did worse than guessing."""
    best = min(rows, key=lambda r: r[1])
    text = f"  Best: {best[0]} ({best[1]:.3f})."
    worse = [name for name, brier in rows if brier >= COIN_FLIP]
    if worse:
        text += f"\n  Worse than a coin flip: {', '.join(worse)}. Don't trust it with this question."
    return text


def main() -> None:
    players = contenders()
    width = max(len(name) for name, _ in players) + 2
    print("\nBrier score: 0 is perfect, 0.25 is a coin flip (│). Shorter bars are better.")

    for n, (title, labels, question) in enumerate(ROUNDS, 1):
        # 1. The question, and a set of examples where we know the right answer.
        print(f"\nRound {n} · {title} ({len(labels)} labelled examples)\n  Q: {question}")
        wait("press Enter to run this round")
        print(f"  {'':{width}}{'Brier, lower = better':22}score    acc     speed")

        rows = []
        for name, ask in players:
            ask(next(iter(labels)), question)  # warm-up: model load / connection, not timed

            # 2. Ask every example, and time it.
            start = time.perf_counter()
            probs = {state: ask(state, question) for state in labels}
            ms = (time.perf_counter() - start) / len(labels) * 1000

            # 3. Compare the probabilities with the right answers.
            brier, accuracy = score(probs, labels)
            brier_row(name, brier, accuracy, ms, width)
            rows.append((name, brier))
        print(verdict(rows))


if __name__ == "__main__":
    main()
