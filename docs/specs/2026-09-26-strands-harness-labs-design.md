# Strands Harness Labs — Design

## Purpose

A private (later public) GitHub repo backing a YouTube series. It teaches the
open-source **Strands Harness SDK** (`strands-harness`, released 2026-09-21)
the same way `syedair/strands-agents-labs` taught the Strands Agents SDK: one
short runnable file per lab, Ollama-first, a README that walks lab by lab.

The second half teaches the **System 1 model** pattern shown in the AWS video
"Jev: Is This Tool Call Ready?" (repo: `mikegc-aws/jev-strands-video`, MIT):
a small classifier answers narrow typed questions with probabilities, and plain
Python turns those probabilities into decisions. Jev itself is a hosted,
closed model; here the classifier is a small open model running locally on
Ollama.

## Guiding rules

- **Simple and progressive.** One running example — a travel assistant — is
  created in lab 1 and each lab adds exactly one idea to it. A viewer can
  diff lab N against lab N-1 and see the one new thing.
- **Readable on camera.** Each lab file is short, starts with a one-line
  purpose comment, and prints a trace of what is happening. Readability beats
  robustness; no retries or abstraction layers.
- **Runs locally with no cloud account.** Defaults are all Ollama. Bedrock
  (Claude) is a one-line `.env` change for the main model.

## Models

| Role | Setting | Default | Alternative |
|---|---|---|---|
| Main agent (the harness) | `MAIN_MODEL` in `.env` | `ollama/gpt-oss:20b` | `bedrock/us.anthropic.claude-sonnet-5` |
| System 1 classifier | `SYSTEM1_MODEL` in `.env` | `qwen3.5:4b` (3.4 GB) | `qwen3.5:9b` |

The classifier always runs on Ollama. Lab 9 also reads `SMALL_MODEL` /
`BIG_MODEL` for routing.

## Lab list

The travel assistant evolves through the labs.

| # | File | Adds | Harness feature |
|---|---|---|---|
| 1 | `lab1_first_harness.py` | The assistant exists; compared with a hand-built `Agent` | `create_harness(model=...)`, `instructions` |
| 2 | `lab2_builtin_tools.py` | Looks up real weather/info on the web | `builtin_tools` (pin to `web_fetch`, `read`, `write`) |
| 3 | `lab3_sessions_memory.py` | Remembers the user's home city across runs | `session`, `memory` in `.agent/` |
| 4 | `lab4_skills.py` | A packing-list skill | `skills` from `.agent/skills/packing-list/` |
| 5 | `lab5_interventions.py` | Asks before writing a file | `interventions="ask"`, then a plain-English policy |
| 6 | `lab6_system1_basics.py` | No agent: ask the classifier yes/no and choice questions | `labs/common/system1.py` |
| 7 | `lab7_tool_call_gate.py` | Blocks guessed tool arguments ("What's the weather?" with no city) | custom `InterventionHandler.before_tool_call` → `Guide` / `Proceed` |
| 8 | `lab8_completion_check.py` | Sends the agent back when it stops before the task is done | `after_model_call` → `Guide` / `Proceed` |
| 9 | `lab9_model_switching.py` | Picks small vs big model per request | `ModelRouter` with a strategy driven by a System 1 `choice()` |

Labs 7–9 mirror Mike Chambers' three Strands demos, rebuilt on the harness
with the local classifier. Lab 6 mirrors his `jev_basics` notebook as a
script.

## Components

```
strands-harness-labs/
├── README.md          # old-repo format: Quick Start, Lab Overview, Troubleshooting,
│                      # a video-link line per lab, Credits
├── LICENSE            # MIT
├── pyproject.toml     # uv project; strands-harness[ollama], ollama, python-dotenv, pytest
├── .env.example
├── .gitignore         # .env, .agent/sessions, __pycache__
├── .agent/skills/packing-list/SKILL.md
├── labs/
│   ├── common/config.py    # load .env, expose MAIN_MODEL etc.
│   ├── common/system1.py   # yes_no(), choice()
│   └── lab1_…py … lab9_…py
├── tests/test_system1.py
└── docs/specs/
```

### `labs/common/system1.py`

The only non-trivial code. Two functions:

- `yes_no(state, question) -> float` — probability the answer is yes.
- `choice(state, question, options) -> dict[str, float]` — probability per option label.

Each call is one Ollama `/api/chat` request with `think: false`,
`num_predict: 1`, `temperature: 0`, `logprobs: true`, `top_logprobs: 20`. The
function sums the probabilities of case/space variants of each label ("yes",
"Yes", " yes"), then normalizes across the labels. A label that does not
appear in the top 20 gets 0. Several questions about the same state run in
parallel with a thread pool.

Verified on 2026-09-26 against local Ollama 0.34.4 with `qwen3.5:9b`:
logprobs are returned per token with `top_logprobs`, e.g. P(no)=0.74,
P(yes)=0.26 for an ungrounded-argument question.

## Errors

- Ollama not running or model not pulled: the lab stops with one line naming the
  fix (`ollama serve`, `ollama pull qwen3.5:4b`).
- No other error handling; the labs are teaching code.

## Testing

- `tests/test_system1.py`: unit tests of the probability maths against a faked
  Ollama response (variants summed, normalization, missing label → 0).
- Before completion, every lab is run end to end against local Ollama and its
  output checked by eye; results noted in the PR/commit.

## Out of scope

- A notebook, TypeScript, or the Strands CLI.
- Calling hosted Jev, Laya or Kev (possible later episode).
- A `score()` question type (no lab needs it).

## Delivery

- Local repo at `~/Documents/projects/strands-harness-labs`.
- GitHub: `syedair/strands-harness-labs`, **private**; made public later by the user.
- Video links in the README are placeholders until each video is published.
