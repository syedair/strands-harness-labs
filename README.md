# Strands Harness Labs

Hands-on labs for the open-source [Strands Harness SDK](https://strandsagents.com/docs/user-guide/harness/)
and the **System 1** pattern. You build one travel assistant, one idea per lab: the harness
basics first, then a fast classifier that watches the agent and lets plain Python decide.
By lab 9 the assistant looks up the forecast, remembers where you live, writes a packing
list, asks before saving it, blocks guessed tool calls, finishes what it started, and uses
the expensive model only when the request needs it.

## 🚀 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com) (for the System 1 classifier, labs 6–10)
- AWS credentials with Amazon Bedrock access (for the main agent, by default)

### Installation

```bash
uv sync
cp .env.example .env
ollama pull qwen3.5:4b
```

### Choosing the main model

The agent runs on **Kimi K2.5 on Bedrock** by default ($0.60 / $3.00 per million tokens).
Swap it with one line in `.env`:

```bash
MAIN_MODEL=bedrock/moonshotai.kimi-k2.5          # default
MAIN_MODEL=bedrock/nvidia.nemotron-super-3-120b  # cheapest
MAIN_MODEL=bedrock/us.anthropic.claude-sonnet-5  # Claude
MAIN_MODEL=bedrock/us.moonshotai.kimi-k3         # latest Kimi
MAIN_MODEL=ollama/gpt-oss:20b                    # free and fully local (ollama pull gpt-oss:20b)
```

Lab 9 routes between `SMALL_MODEL` and `BIG_MODEL` (Kimi K2.5 and Kimi K3 on Bedrock by default); for a
fully local lab 9, set those to `ollama/` models too.

### Choosing the System 1 model

Labs 6–9 use `SYSTEM1_MODEL` as the classifier. Pick one in `.env`:

| `SYSTEM1_MODEL` | What it is | Setup |
|---|---|---|
| `ollama/qwen3.5:4b` (default) | A small local chat model as a **stand-in**: one token + its probabilities | `ollama pull qwen3.5:4b` |
| `jev` | TypeSafe's hosted System 1 model (paid) | `TYPESAFE_API_KEY=...` in `.env` ([typesafe.ai](https://typesafe.ai)) |
| `kev` | [Kev](https://github.com/jaredpalmer/kev), an open Jev-alike on your machine (Kev-4B needs a 32 GB Mac) | Start its server (see lab 10), `KEV_URL` in `.env` |
| `laya` | [Laya](https://github.com/NandhaKishorM/laya), an open BERT-based System 1 model | `uv sync --extra laya` |

The labs don't change: `yes_no()` and `choice()` in `labs/common/system1.py` send the same questions to
whichever you pick. Lab 10 runs all four side by side.

## 📚 Lab Overview

Each lab is one short file. Lab N adds exactly one idea to lab N-1, so a diff shows the new thing.

### Lab 1: Your First Harness
**File:** `labs/lab1_first_harness.py`
One `create_harness()` call next to a hand-built `Agent`.
**What's new:** `create_harness(model=..., instructions=...)`
**Video:** _coming soon_
**Run:** `uv run labs/lab1_first_harness.py`

### Lab 2: Built-in Tools
**File:** `labs/lab2_builtin_tools.py`
The assistant fetches the real forecast without you writing a tool.
**What's new:** `builtin_tools=["web_fetch", "read", "write"]`
**Video:** _coming soon_
**Run:** `uv run labs/lab2_builtin_tools.py`

### Lab 3: Sessions & Memory
**File:** `labs/lab3_sessions_memory.py`
Tell it where you live once; a new process still knows.
**What's new:** `session={"id": "travel"}`, `memory=True`
**Video:** _coming soon_
**Run:** (`./reset.sh` first, so it doesn't already remember you)
```bash
uv run labs/lab3_sessions_memory.py tell
uv run labs/lab3_sessions_memory.py ask
```

### Lab 4: Skills
**File:** `labs/lab4_skills.py`
A packing-list skill written in markdown (`.agent/skills/packing-list/SKILL.md`), not code.
**What's new:** `skills=True`
**Video:** _coming soon_
**Run:** `uv run labs/lab4_skills.py`

### Lab 5: Interventions
**File:** `labs/lab5_interventions.py`
Approve tool calls in the terminal, then replace the prompts with a plain-English rule.
**What's new:** `interventions=HumanInTheLoop(ask="stdio")`, `resolve_interventions("<policy>")`
**Video:** _coming soon_
**Run:**
```bash
uv run labs/lab5_interventions.py          # approve every call
uv run labs/lab5_interventions.py policy   # a policy decides
```

### Lab 6: System 1 Basics
**File:** `labs/lab6_system1_basics.py`
No agent. A small local model answers yes/no and choice questions with probabilities.
**What's new:** `common/system1.py` — `yes_no()`, `yes_no_many()`, `choice()` (try `SYSTEM1_MODEL=jev`)
**Video:** _coming soon_
**Run:** `uv run labs/lab6_system1_basics.py`

### Lab 7: Tool-Call Gate
**File:** `labs/lab7_tool_call_gate.py`
"What's the weather?" with no city: the agent guesses Seattle, the classifier catches the guess,
and the agent asks you instead. A real city goes straight through.
**What's new:** a custom `InterventionHandler.before_tool_call` returning `Guide` / `Proceed`
**Video:** _coming soon_
**Run:** `uv run labs/lab7_tool_call_gate.py`

### Lab 8: Completion Check
**File:** `labs/lab8_completion_check.py`
The agent answers only half the question; the classifier notices and sends it back.
**What's new:** `after_model_call` returning `Guide` (capped at two retries)
**Video:** _coming soon_
**Run:** `uv run labs/lab8_completion_check.py`

### Lab 9: Model Switching
**File:** `labs/lab9_model_switching.py`
Quick questions go to Kimi K2.5, big planning requests to Kimi K3.
**What's new:** `create_harness(model=ModelRouter([...], strategy=...))`
**Video:** _coming soon_
**Run:** `uv run labs/lab9_model_switching.py`

### Lab 10: System 1 Showdown
**File:** `labs/lab10_system1_showdown.py`
Jev (paid) vs Kev (open) vs Laya (open) vs our Qwen stand-in, on labelled travel questions.
Contenders you haven't set up are skipped with a one-line hint.
**What's new:** Brier score and accuracy; abstract vs concrete questions
**Video:** _coming soon_
**Setup (each optional):**
```bash
export TYPESAFE_API_KEY=...        # Jev — https://typesafe.ai
uv sync --extra laya               # Laya — pulls in PyTorch
# Kev — in a clone of github.com/jaredpalmer/kev:
uv sync --extra serve && uv run --extra serve python -m kev.serve --run jaredpalmer/kev-4b --port 8009
```
**Run:** `uv run labs/lab10_system1_showdown.py`

## 🧠 What is a System 1 model?

Jev (TypeSafe) is a "System 1" model: instead of writing text, it answers narrow, typed questions
— yes/no, pick one, score — in a single pass and returns calibrated probabilities. It never decides
anything; your code reads the probabilities and decides. Kev and Laya are open models built the
same way. Labs 6–9 use a small general chat model (`qwen3.5:4b`) as a **stand-in**: it generates
exactly one token and we read the probabilities of "yes" and "no". It's fast (~0.1 s a question) and
works well on concrete questions; lab 10 shows where a real System 1 model does better.

## 🆘 Troubleshooting

- **"Ollama isn't reachable"** — start it with `ollama serve`.
- **"Model … isn't pulled"** — run the `ollama pull` command the lab prints.
- **Bedrock `AccessDeniedException`** — enable the model in the Bedrock console and check your AWS credentials and `AWS_REGION`.
- **Start fresh** — `./reset.sh` clears sessions, memory and saved packing lists (skills are kept)
- **First System 1 call is slow** — Ollama is loading the model; later calls take about 0.1 s.
- **Warnings about prompt caching** — some models don't support it; the labs still work.

## 🙏 Credits

- [Mike Chambers — jev-strands-video](https://github.com/mikegc-aws/jev-strands-video) (MIT): the System 1 + Strands interventions pattern that labs 7–9 rebuild on the harness.
- [TypeSafe Jev](https://typesafe.ai), [Kev](https://github.com/jaredpalmer/kev), [Laya](https://github.com/NandhaKishorM/laya).
- The beach-destination set in lab 10 comes from the author's `systemone-model-typesafeai` demo.
- [Strands Agents](https://strandsagents.com) and the [Strands Harness SDK](https://github.com/strands-agents/harness-sdk).

## 📄 License

MIT — see [LICENSE](LICENSE).
