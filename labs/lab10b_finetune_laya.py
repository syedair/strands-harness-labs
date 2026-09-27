# Lab 10b: fine-tune Laya on travel data.
#
# Lab 10 showed Laya is the fastest System 1 model here and the weakest: close to a coin flip on our tool-call
# questions. Laya's own docs say it: a fast base to specialise, not a zero-shot decision engine. So we specialise
# it: Kev (slow, good) labels a few hundred travel questions, and Laya (fast) learns to copy those probabilities.
# That's distillation. Then we re-run lab 10's rounds on questions Laya never trained on.
#
# Needs: Laya (uv sync --extra laya --inexact), a teacher (Kev running, or TEACHER=jev with TYPESAFE_API_KEY),
# and a GPU: measured ~2 minutes and ~11 GB on an Apple M4 Max. On CPU it runs, but slowly.
# The recipe comes from Laya's own notebook: docs/reference/laya/.
import os
import sys
import time
from functools import partial

from common import config
from common.show import brier_row, wait
from common.showdown import score
from common.system1 import check_system1, display_name, laya_installed, unavailable, yes_no
from common.travel_data import label, training_questions
from lab10_system1_showdown import ROUNDS, verdict

TEACHER = os.environ.get("TEACHER", "kev")
EPOCHS = int(os.environ.get("EPOCHS", "4"))
OUT = config.LAYA_TRAVEL_DIR


def showdown(players) -> None:
    """Lab 10's three rounds: the same held-out questions, never used for training."""
    width = max(len(name) for name, _ in players) + 2
    for n, (title, labels, question) in enumerate(ROUNDS, 1):
        print(f"\nRound {n} · {title} ({len(labels)} labelled examples)\n  Q: {question}")
        print(f"  {'':{width}}{'Brier, lower = better':22}score    acc     speed")
        rows = []
        for name, ask in players:
            ask(next(iter(labels)), question)  # warm-up, not timed
            start = time.perf_counter()
            probs = {state: ask(state, question) for state in labels}
            ms = (time.perf_counter() - start) / len(labels) * 1000
            brier, accuracy = score(probs, labels)
            brier_row(name, brier, accuracy, ms, width)
            rows.append((name, brier))
        print(verdict(rows))


def main() -> None:
    if not laya_installed():  # a cheap check: loading Laya here would sit on the GPU during training
        print("Laya isn't installed. Run: uv sync --extra laya --inexact")
        sys.exit(1)
    import laya

    from common import laya_train  # needs torch, which the laya extra brings

    retrain = "--skip-train" not in sys.argv
    if not retrain and not (OUT / "model.safetensors").exists():
        print("No fine-tuned model yet. Run it once without --skip-train.")
        sys.exit(1)
    device = laya_train.pick_device()
    print(f"Training device: {device}" + ("   (no GPU found: this will be slow)" if device == "cpu" else ""))

    if retrain:
        check_system1(TEACHER)
        teacher = display_name(TEACHER)

        # 1. Travel questions that share nothing with lab 10's held-out rounds.
        pairs = training_questions()
        print(f"\n1 · {len(pairs)} training questions: new destinations, and weather tool calls where the city was "
              "given, was a different one, or was a guess.")
        for state, question in (pairs[0], pairs[-2], pairs[-1]):
            print(f"    {' · '.join(line for line in state.splitlines() if line)}\n      → {question}")
        wait(f"press Enter to have {teacher} label them")

        # 2. The teacher labels them. We keep its probability, not just yes or no.
        start = time.perf_counter()
        rows = label(pairs, TEACHER, OUT / "labels.json")
        print(f"\n2 · {teacher} labelled {len(rows)} questions in {time.perf_counter() - start:.0f}s "
              f"(cached in {OUT.relative_to(config.LAYA_TRAVEL_DIR.parents[1])}/labels.json)")
        wait(f"press Enter to train Laya on {device}")

        # 3. Train: Laya learns to give the teacher's probabilities. Then calibrate on held-out questions.
        print(f"\n3 · Training Laya (421M parameters) for {EPOCHS} epochs on {device}")
        stats = laya_train.train(rows, OUT, EPOCHS, device)
        peak = f", peak memory {stats['peak_gb']:.1f} GB" if stats["peak_gb"] else ""
        print(f"    trained on {stats['items']} questions in {stats['seconds']:.0f}s{peak}; "
              f"calibration temperature {stats['temperature']:.2f}")
    wait("press Enter to compare it with base Laya on lab 10's questions")

    # 4. Before and after, on questions it never trained on.
    print("\n4 · Before and after. Brier: 0 is perfect, 0.25 is a coin flip (│).")
    players = [("laya (base)", laya_train.asker(laya.Agent(laya_train.base_model_dir(), device=device))),
               ("laya (fine-tuned)", laya_train.asker(laya.Agent(str(OUT), device=device)))]
    if unavailable(TEACHER) is None:
        players.append((f"{TEACHER} (teacher)", partial(yes_no, model=TEACHER)))
    showdown(players)


if __name__ == "__main__":
    main()
