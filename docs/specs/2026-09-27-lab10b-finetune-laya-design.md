# Lab 10b: Fine-tune Laya on travel data (design)

## Why this lab

Lab 10 shows Laya is the fastest System 1 model here (~19 ms) and the weakest (Brier 0.23 on tool calls, about a
coin flip). Laya's own docs say the same: "Treat Laya as a fast base to specialise, not as a zero-shot decision
engine." Lab 10b shows the other half: **Laya isn't great out of the box, but you can train it on your own data in a
couple of minutes on a laptop.** We train it on travel questions, labelled by Kev, and re-run the showdown.

The message for the video, in order:
1. Laya zero-shot is weak on our questions (lab 10's numbers).
2. Fine-tuning is cheap: a few hundred labelled examples, ~2 minutes, ~11 GB of GPU memory.
3. We don't hand-label: Kev (slow, good) labels the examples, and Laya (fast) learns from it. That's distillation.
4. On lab 10's held-out questions, fine-tuned Laya gets close to Kev at a fraction of the time.

## Update after building it

The final lab also trains on lab 7's four gate questions (in the gate's own format), so `SYSTEM1_MODEL=laya-travel`
runs lab 7 properly: 1,955 questions, ~3 min labelling, ~6 min training, 14.1 GB peak on an M4 Max. Hardware
guidance rose to Apple Silicon 24 GB+ / NVIDIA 16 GB+. Starting from `laya-typed-decisions` was measured and
rejected (no better on travel). Numbers are in the README.

## Evidence (feasibility spike, 2026-09-27)

Measured on an Apple M4 Max (51 GB), Kev-4B as teacher, 764 Kev-labelled questions, 4 epochs, lab 10's held-out sets:

| Round | Base Laya | Fine-tuned Laya | Kev |
|---|---|---|---|
| Tool calls, concrete (12) | 0.230 · 67% | 0.019 · 100% | 0.015 · 100% |
| Tool calls, abstract (12) | 0.240 · 67% | 0.111 · 92% | 0.098 · 83% |
| Beach destinations (44) | 0.137 · 80% | 0.114 · 84% | 0.032 · 98% |

Labelling took 86 s; training 127 s; peak GPU memory 10.8 GB; speed unchanged (~18 ms per question).
Beach barely improved with 164 destinations: the lab says so rather than hiding it.

## Where the recipe comes from

Laya's fine-tuning notebook is copied unchanged, with its Apache-2.0 licence and source commit, to
`docs/reference/laya/` so viewers can open it. It trains on `LocalLLaMA/typed-decisions`, whose labels come from "a
teacher endpoint of roughly 4B-class capability" (not named on the dataset card), sampled 3 times at temperature 0.7
and averaged. Lab 10b follows the same recipe with Kev-4B as the teacher. The lab and README say two things plainly:

- **We don't know which model labelled Laya's dataset.** We don't claim it was Kev.
- **Kev is deterministic** (identical probabilities on repeat calls), so averaging 3 samples would change nothing; we
  take one. The dataset card warns its scores measure agreement with the teacher, not correctness. Lab 10b tests
  against lab 10's hand-checked answers instead, so its before/after measures being right.

## Script, not notebook

The lab is a Python script, like every other lab: it runs with `uv run`, pauses between steps for narration, is
tested, and doesn't need Jupyter. The video opens the reference notebook to show where the recipe comes from, then
runs the script.

## Hardware and requirements (stated in the README and printed by the lab)

- **Measured:** Apple Silicon (M4 Max), PyTorch on the Apple GPU (MPS): ~2 minutes, 10.8 GB peak.
- **Guidance:** a Mac with Apple Silicon and 16 GB+ unified memory, or an NVIDIA GPU with 12 GB+ memory. On CPU it
  runs, but slowly (not measured; the lab warns). These last two are untested: the README marks them as guidance.
- **Teacher:** Kev running locally (`./kev.sh start`; Kev-4B needs a 32 GB Mac) or Jev (`TYPESAFE_API_KEY`).
- **Laya installed:** `uv sync --extra laya --inexact`. The base model (421M parameters) downloads on first run.
- **Disk:** the fine-tuned model is ~0.9 GB, saved under `models/laya-travel/` (gitignored).

## What the lab does (`labs/lab10b_finetune_laya.py`)

Four numbered steps, each paused before it runs (same style and `wait()` as labs 6–10; no pauses off a terminal):

1. **Build travel training data** that shares nothing with lab 10's held-out sets: ~160 new destinations for the
   beach question; ~300 tool calls generated from message templates × cities (the city given, a different city, or
   none). Asserts no overlap with `BEACH` / `TOOL_CALLS`. Prints counts and three examples.
2. **Label with the teacher** (Kev by default; `TEACHER=jev` to switch). Soft labels (the teacher's probability), cached
   to `models/laya-travel/labels.json` so a second run skips this step. Prints time taken.
3. **Train**: the loop from Laya's fine-tuning notebook (proper-scoring-rule rewards plus soft cross-entropy), adapted
   to one device: `mps`, else `cuda`, else `cpu` with a warning. Prints the device, one line per epoch (loss, time),
   and peak memory. Then fits the yes/no calibration temperature on a held-out 10% slice and saves the model.
4. **Before and after**: runs lab 10's three rounds with base Laya and fine-tuned Laya on the same checkpoint family,
   drawn with `brier_row` bars and the coin-flip line, and a verdict per round.

Flags: `--skip-train` re-runs step 4 with the saved model. `EPOCHS` env var (default 4).

## Using the trained model elsewhere

- **Lab 10 showdown** adds `laya-travel (fine-tuned)` as a fifth contender when `models/laya-travel/` exists.
- **`SYSTEM1_MODEL=laya-travel`** makes labs 6e–9 (and lab 11) use it, through the same `yes_no` / `yes_no_many`
  helpers. `display_name()` returns "Laya (fine-tuned on travel)".

## Code layout

- `labs/lab10b_finetune_laya.py`: the four steps, readable top to bottom, numbered comments like labs 6–10.
- `labs/common/travel_data.py`: the destination list, message templates and `training_questions()`; no model code.
- `labs/common/laya_train.py`: `train(items, out_dir, epochs, device)` and `fit_temperature()`, adapted from Laya's
  notebook, with a link and credit in the file and README (Laya is Apache-2.0).
- `labs/common/system1.py`: a `laya-travel` backend (loads `laya.Agent(models/laya-travel)` once, cached).
- `labs/common/showdown.py`: the optional fifth contender.

## Tests (no model download, no training)

- training data never overlaps lab 10's held-out sets, and covers all three tool-call kinds;
- labels are cached and reused; `TEACHER` picks the backend;
- device choice: mps, then cuda, then cpu;
- the fifth contender appears only when the model folder exists;
- `SYSTEM1_MODEL=laya-travel` resolves, `display_name` names it, and `unavailable` explains how to create it.

## Video and docs

- README: a Lab 10b section with the message, the hardware table, the run command, and the spike's numbers labelled
  as "measured on an M4 Max".
- Diagram `lab10b-finetune-laya`: teacher (Kev) → labels → Laya training → before/after bars, the hardware note, and
  the idea line "Laya isn't great out of the box. Two minutes of training on your laptop fixes that."
- Script: a Lab 10b section in the same short-sentence style.

## Out of scope

- Pushing the model to the Hugging Face Hub.
- Choice and Score questions (the showdown only asks yes/no).
- Tuning the beach round further; the lab reports the modest gain as it is.
