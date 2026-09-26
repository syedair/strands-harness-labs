# Strands Harness Labs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build nine short, progressive lab scripts that teach the Strands Harness SDK and the System 1 classifier pattern through one evolving travel assistant.

**Architecture:** Each lab is one standalone script in `labs/` that runs with `uv run`. Two shared modules keep the labs short: `labs/common/config.py` (settings from `.env`, Ollama pre-check) and `labs/common/system1.py` (yes/no and choice questions answered with probabilities from Ollama logprobs). Lab N differs from lab N-1 by exactly one idea.

**Tech Stack:** Python 3.13, uv, `strands-harness[ollama]` 0.1.x (pulls `strands-agents` >=1.56), `httpx`, `python-dotenv`, pytest, Ollama 0.34.

**Spec:** `docs/specs/2026-09-26-strands-harness-labs-design.md`

## Global Constraints

- Python `>=3.13`; dependency `strands-harness[ollama]>=0.1.2,<0.2`.
- Defaults (all local): `MAIN_MODEL=ollama/gpt-oss:20b`, `SYSTEM1_MODEL=qwen3.5:4b`, `SMALL_MODEL=qwen3.5:9b`, `BIG_MODEL=gpt-oss:20b`, `OLLAMA_HOST=http://127.0.0.1:11434`.
- Bedrock is a one-line `.env` change for the main model only: `MAIN_MODEL=bedrock/us.anthropic.claude-sonnet-5`. The classifier always runs on Ollama.
- Every lab file: first line is a one-line purpose comment; short; prints a readable trace; `if __name__ == "__main__": main()`.
- Labs switch harness features off by default and turn on only the one they teach (`builtin_tools=[]`, `session=False`, `memory=False`, `skills=False` unless the lab is about it).
- Every System 1 request sets `think: false`, `num_predict: 1`, `temperature: 0`, `logprobs: true`, `top_logprobs: 20`.
- Run scripts from the repo root: `uv run labs/<file>.py`. Scripts import shared code as `from common.config import ...` (the script's folder is on `sys.path`); pytest uses `pythonpath = ["labs"]`.
- Credit `mikegc-aws/jev-strands-video` (MIT) in the README; write fresh code, do not copy files.
- Git: first commit (spec + plan) goes to `main`; all lab work is on branch `labs-v1`, delivered by PR.

## Review Focus

1. **Ollama not running, or a model not pulled** → the lab prints one line with the fix (`ollama serve` / `ollama pull qwen3.5:4b`) and exits 1; no stack trace. Test in Task 1.
2. **Neither label appears in the classifier's top 20 tokens** → probabilities come back uniform instead of crashing on divide-by-zero. Test in Task 6.
3. **Thinking left on for Qwen** → the first token would be a think tag and every answer uniform. The request payload must carry `think: false`. Test in Task 6.
4. **Completion check never converges** (Guide on `after_model_call` retries forever) → capped at `MAX_GUIDES = 2`, then Proceed. Built into Task 8.
5. **Stale `.agent/` state from an earlier take** makes lab 3's "first run" already remember the city → `.agent/sessions` and `.agent/memory` are git-ignored and the README gives the reset command. Task 3 and Task 10.

---

### Task 1: Project scaffold, config, and lab 1 (first harness)

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`, `LICENSE`, `.python-version`
- Create: `labs/common/__init__.py` (empty), `labs/common/config.py`
- Create: `labs/lab1_first_harness.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `common.config` constants `MAIN_MODEL, SYSTEM1_MODEL, SMALL_MODEL, BIG_MODEL, OLLAMA_HOST` (all `str`) and `check_ollama(*models: str) -> None` (prints fix and `sys.exit(1)` on failure).

- [ ] **Step 1: Create the branch and scaffold files**

```bash
cd ~/Documents/projects/strands-harness-labs
git checkout -b labs-v1
echo "3.13" > .python-version
mkdir -p labs/common tests
touch labs/common/__init__.py
```

`pyproject.toml`:

```toml
[project]
name = "strands-harness-labs"
version = "0.1.0"
description = "Hands-on labs for the Strands Harness SDK and System 1 classifiers"
requires-python = ">=3.13"
dependencies = [
    "strands-harness[ollama]>=0.1.2,<0.2",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["labs"]
```

`.env.example`:

```bash
# Main agent. Default is local; for Claude on Bedrock use:
# MAIN_MODEL=bedrock/us.anthropic.claude-sonnet-5
MAIN_MODEL=ollama/gpt-oss:20b

# System 1 classifier (always Ollama). qwen3.5:9b is more accurate, slower.
SYSTEM1_MODEL=qwen3.5:4b

# Lab 9 routes between these two Ollama models.
SMALL_MODEL=qwen3.5:9b
BIG_MODEL=gpt-oss:20b

OLLAMA_HOST=http://127.0.0.1:11434
```

`.gitignore`:

```
.env
.venv/
__pycache__/
.pytest_cache/
.agent/sessions/
.agent/memory/
trips/
```

`LICENSE`: standard MIT text, `Copyright (c) 2026 Syed Humair`.

- [ ] **Step 2: Write the failing config test**

`tests/test_config.py`:

```python
import pytest

from common import config


def test_check_ollama_exits_with_pull_hint_when_model_missing(monkeypatch, capsys):
    monkeypatch.setattr(config, "_pulled_models", lambda: {"gpt-oss:20b"})
    with pytest.raises(SystemExit) as exit_info:
        config.check_ollama("gpt-oss:20b", "qwen3.5:4b")
    assert exit_info.value.code == 1
    assert "ollama pull qwen3.5:4b" in capsys.readouterr().out


def test_check_ollama_exits_with_serve_hint_when_ollama_down(monkeypatch, capsys):
    def down():
        raise config.httpx.ConnectError("refused")

    monkeypatch.setattr(config, "_pulled_models", down)
    with pytest.raises(SystemExit):
        config.check_ollama("qwen3.5:4b")
    assert "ollama serve" in capsys.readouterr().out


def test_check_ollama_accepts_latest_tag(monkeypatch):
    monkeypatch.setattr(config, "_pulled_models", lambda: {"qwen3.5:4b"})
    config.check_ollama("qwen3.5:4b")  # no exit


def test_check_ollama_ignores_non_ollama_main_model(monkeypatch):
    monkeypatch.setattr(config, "_pulled_models", lambda: set())
    config.check_ollama("bedrock/us.anthropic.claude-sonnet-5")  # no exit
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` for `common.config`.

- [ ] **Step 4: Implement `labs/common/config.py`**

```python
# Shared settings for every lab, read from .env.
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

MAIN_MODEL = os.environ.get("MAIN_MODEL", "ollama/gpt-oss:20b")
SYSTEM1_MODEL = os.environ.get("SYSTEM1_MODEL", "qwen3.5:4b")
SMALL_MODEL = os.environ.get("SMALL_MODEL", "qwen3.5:9b")
BIG_MODEL = os.environ.get("BIG_MODEL", "gpt-oss:20b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def _pulled_models() -> set[str]:
    response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    response.raise_for_status()
    return {model["name"] for model in response.json()["models"]}


def check_ollama(*models: str) -> None:
    """Exit with a one-line fix if Ollama is down or a model isn't pulled."""
    wanted = [m.removeprefix("ollama/") for m in models if "/" not in m.removeprefix("ollama/")]
    if not wanted:
        return
    try:
        pulled = _pulled_models()
    except httpx.HTTPError:
        print(f"Ollama isn't reachable at {OLLAMA_HOST}. Start it with: ollama serve")
        sys.exit(1)
    for model in wanted:
        if model not in pulled and f"{model}:latest" not in pulled:
            print(f"Model {model} isn't pulled. Run: ollama pull {model}")
            sys.exit(1)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 6: Write `labs/lab1_first_harness.py`**

```python
# Lab 1: your first harness — one call gives you a ready-made agent.
from strands import Agent
from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = "You are a friendly travel assistant. Keep answers short and practical."


def main() -> None:
    check_ollama(MAIN_MODEL)

    # The old way (strands-agents-labs, lab 1): you assemble the agent yourself.
    plain = Agent(system_prompt=INSTRUCTIONS)
    print(f"Hand-built Agent tools: {plain.tool_names}")

    # The harness way: one call, tested defaults. We switch the extras off for now;
    # each later lab turns on exactly one of them.
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=[],
        session=False,
        memory=False,
        skills=False,
    )
    print(f"Harness agent is a {type(agent).__name__} running on {MAIN_MODEL}\n")

    agent("I have a free weekend in March. Suggest one city break from Dubai and why.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run lab 1 end to end**

Run: `cp .env.example .env && uv run labs/lab1_first_harness.py`
Expected: prints `Hand-built Agent tools: []`, `Harness agent is a Agent running on ollama/gpt-oss:20b`, then a short city-break suggestion streamed to the terminal. A caching warning for Ollama is acceptable. If `create_harness` rejects any keyword, read `create_harness`'s docstring in the installed package and fix the call; do not add workarounds.

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "Scaffold project, shared config, and lab 1 (first harness)"
```

---

### Task 2: Lab 2 — built-in tools

**Files:**
- Create: `labs/lab2_builtin_tools.py`

**Interfaces:**
- Consumes: `common.config.MAIN_MODEL`, `check_ollama`.

- [ ] **Step 1: Write the lab**

```python
# Lab 2: built-in tools — the assistant looks up the real forecast with no tool code written.
from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch", "read", "write"],  # NEW: pin exactly the tools we want
        session=False,
        memory=False,
        skills=False,
    )
    print(f"Tools this agent can use: {agent.tool_names}\n")

    agent("What's the weather in Istanbul right now?")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run labs/lab2_builtin_tools.py`
Expected: tool list includes `web_fetch`, `read`, `write`; the agent calls `web_fetch` on a `wttr.in/Istanbul` URL and reports a real temperature.

- [ ] **Step 3: Commit**

```bash
git add labs/lab2_builtin_tools.py
git commit -m "Add lab 2: built-in tools"
```

---

### Task 3: Lab 3 — sessions and memory

**Files:**
- Create: `labs/lab3_sessions_memory.py`

**Interfaces:**
- Consumes: `common.config.MAIN_MODEL`, `check_ollama`.

- [ ] **Step 1: Write the lab**

```python
# Lab 3: sessions & memory — the assistant remembers where you live, across runs.
import sys

from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch.\n"
    "When the user tells you a lasting personal fact (home city, preferences), save it to memory."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session={"id": "travel"},  # NEW: conversation saved under .agent/sessions/travel
        memory=True,  # NEW: long-term notes saved as markdown under .agent/memory
        skills=False,
    )

    # Run 1: python lab3_sessions_memory.py tell
    # Run 2: python lab3_sessions_memory.py ask   (a fresh process — nothing in RAM)
    if sys.argv[1:] == ["tell"]:
        agent("By the way, I live in Dubai.")
    else:
        agent("What's the weather like at home today?")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it twice, from a clean state**

Run:
```bash
rm -rf .agent/sessions .agent/memory
uv run labs/lab3_sessions_memory.py tell
uv run labs/lab3_sessions_memory.py ask
ls .agent/memory
```
Expected: run 2 answers with Dubai weather without being told the city; `.agent/memory` contains a markdown note mentioning Dubai.

- [ ] **Step 3: Commit**

```bash
git add labs/lab3_sessions_memory.py
git commit -m "Add lab 3: sessions and memory"
```

---

### Task 4: Lab 4 — skills

**Files:**
- Create: `.agent/skills/packing-list/SKILL.md`
- Create: `labs/lab4_skills.py`

**Interfaces:**
- Consumes: `common.config.MAIN_MODEL`, `check_ollama`.

- [ ] **Step 1: Write the skill**

`.agent/skills/packing-list/SKILL.md`:

```markdown
---
name: packing-list
description: Build a packing list for a trip from the destination, dates, and forecast.
---

# Packing list

1. Get the forecast for the destination (wttr.in).
2. Write the list as markdown with these sections, in order:
   **Clothes**, **Toiletries**, **Documents**, **Tech**, **Weather extras**.
3. Keep each section to 3–6 items. Put the forecast in one line at the top.
```

- [ ] **Step 2: Write the lab**

```python
# Lab 4: skills — teach the assistant a repeatable task with a markdown file, not code.
from strands_harness import create_harness

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def main() -> None:
    check_ollama(MAIN_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=True,  # NEW: loads .agent/skills/* on demand
    )

    agent("I'm going to Istanbul next week for 4 days. What should I pack?")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it**

Run: `uv run labs/lab4_skills.py`
Expected: the trace shows the `skills` tool loading `packing-list`, then a list with the five section headings in order and a forecast line at the top.

- [ ] **Step 4: Commit**

```bash
git add .agent/skills labs/lab4_skills.py
git commit -m "Add lab 4: skills"
```

---

### Task 5: Lab 5 — interventions

**Files:**
- Create: `labs/lab5_interventions.py`

**Interfaces:**
- Consumes: `common.config.MAIN_MODEL`, `check_ollama`.

- [ ] **Step 1: Write the lab**

```python
# Lab 5: interventions — the assistant asks before it writes a file.
import sys

from strands.vended_interventions.hitl import HumanInTheLoop
from strands_harness import create_harness, resolve_interventions

from common.config import MAIN_MODEL, check_ollama

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch.\n"
    "Save packing lists to trips/<city>-packing-list.md."
)


def main() -> None:
    check_ollama(MAIN_MODEL)

    if sys.argv[1:] == ["policy"]:
        # Part B: a plain-English rule. A classifier decides which calls need your approval.
        interventions = resolve_interventions(
            "Reading and fetching are fine. Writing files is only fine under ./trips.",
            ask="stdio",
        )
    else:
        # Part A: approve every tool call in the terminal.
        interventions = HumanInTheLoop(ask="stdio")

    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch", "write"],
        session=False,
        memory=False,
        skills=True,
        interventions=interventions,  # NEW
    )

    agent("Make me a packing list for 4 days in Istanbul and save it.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run both parts**

Run: `uv run labs/lab5_interventions.py` (answer `y` to each prompt), then `uv run labs/lab5_interventions.py policy`.
Expected part A: a terminal prompt before `web_fetch` and before `write`; after approval `trips/istanbul-packing-list.md` exists. Part B: `web_fetch` runs without a prompt; the write under `trips/` also runs (or prompts once, depending on the classifier). If `HumanInTheLoop` rejects `ask="stdio"`, check its signature in the installed `strands` package and use the documented terminal option.

- [ ] **Step 3: Commit**

```bash
git add labs/lab5_interventions.py
git commit -m "Add lab 5: interventions"
```

---

### Task 6: `system1.py` and lab 6 — System 1 basics

**Files:**
- Create: `labs/common/system1.py`
- Create: `labs/lab6_system1_basics.py`
- Test: `tests/test_system1.py`

**Interfaces:**
- Consumes: `common.config.OLLAMA_HOST`, `SYSTEM1_MODEL`, `check_ollama`.
- Produces:
  - `label_probabilities(top_logprobs: list[dict], labels: list[str]) -> dict[str, float]`
  - `yes_no(state: str, question: str) -> float` — P(yes)
  - `yes_no_many(state: str, questions: dict[str, str]) -> dict[str, float]` — P(yes) per key, asked in parallel
  - `choice(state: str, question: str, options: list[str]) -> dict[str, float]` — P per option

- [ ] **Step 1: Write the failing tests**

`tests/test_system1.py`:

```python
import math

import pytest

from common import system1


def lp(p):
    return math.log(p)


def test_label_probabilities_sums_case_and_space_variants():
    top = [
        {"token": "no", "logprob": lp(0.70)},
        {"token": "yes", "logprob": lp(0.20)},
        {"token": "No", "logprob": lp(0.05)},
        {"token": " yes", "logprob": lp(0.05)},
    ]
    probs = system1.label_probabilities(top, ["yes", "no"])
    assert probs["yes"] == pytest.approx(0.25)
    assert probs["no"] == pytest.approx(0.75)


def test_label_probabilities_ignores_other_tokens_and_renormalizes():
    top = [{"token": "maybe", "logprob": lp(0.5)}, {"token": "yes", "logprob": lp(0.3)}, {"token": "no", "logprob": lp(0.1)}]
    probs = system1.label_probabilities(top, ["yes", "no"])
    assert probs["yes"] == pytest.approx(0.75)


def test_label_probabilities_missing_label_is_zero():
    probs = system1.label_probabilities([{"token": "yes", "logprob": lp(0.9)}], ["yes", "no"])
    assert probs == {"yes": 1.0, "no": 0.0}


def test_label_probabilities_no_labels_present_is_uniform():
    probs = system1.label_probabilities([{"token": "<think>", "logprob": lp(0.9)}], ["a", "b", "c"])
    assert probs == pytest.approx({"a": 1 / 3, "b": 1 / 3, "c": 1 / 3})


def fake_post(tokens, sent):
    def post(payload):
        sent.append(payload)
        return {"logprobs": [{"top_logprobs": [{"token": t, "logprob": lp(p)} for t, p in tokens]}]}

    return post


def test_yes_no_sends_single_token_no_thinking_request(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_post", fake_post([("yes", 0.8), ("no", 0.2)], sent))
    assert system1.yes_no("user: hi", "Is this a greeting?") == pytest.approx(0.8)
    payload = sent[0]
    assert payload["think"] is False
    assert payload["logprobs"] is True
    assert payload["options"]["num_predict"] == 1
    assert payload["options"]["temperature"] == 0


def test_choice_maps_letters_back_to_option_names(monkeypatch):
    sent = []
    monkeypatch.setattr(system1, "_post", fake_post([("b", 0.6), ("A", 0.4)], sent))
    probs = system1.choice("text", "How hard?", ["easy", "hard"])
    assert probs == pytest.approx({"easy": 0.4, "hard": 0.6})
    assert "a) easy" in sent[0]["messages"][-1]["content"]


def test_yes_no_many_keeps_keys(monkeypatch):
    monkeypatch.setattr(system1, "_post", fake_post([("yes", 0.9), ("no", 0.1)], []))
    probs = system1.yes_no_many("state", {"grounded": "Q1?", "premature": "Q2?"})
    assert set(probs) == {"grounded", "premature"}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_system1.py -v`
Expected: FAIL with `ImportError` for `common.system1`.

- [ ] **Step 3: Implement `labs/common/system1.py`**

```python
# System 1: a small local model answers narrow, typed questions with probabilities.
# It never decides anything — your Python code does.
import math
from concurrent.futures import ThreadPoolExecutor

import httpx

from common.config import OLLAMA_HOST, SYSTEM1_MODEL


def _post(payload: dict) -> dict:
    response = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def label_probabilities(top_logprobs: list[dict], labels: list[str]) -> dict[str, float]:
    """Turn the model's top next-token guesses into a probability per label."""
    totals = {label: 0.0 for label in labels}
    for guess in top_logprobs:
        token = guess["token"].strip().lower()  # "Yes", " yes" and "yes" all count as yes
        if token in totals:
            totals[token] += math.exp(guess["logprob"])
    total = sum(totals.values())
    if total == 0:  # none of the labels came up: we learned nothing
        return {label: 1 / len(labels) for label in labels}
    return {label: p / total for label, p in totals.items()}


def _ask(state: str, question: str, labels: list[str]) -> dict[str, float]:
    payload = {
        "model": SYSTEM1_MODEL,
        "think": False,  # answer in one step, no reasoning
        "stream": False,
        "logprobs": True,
        "top_logprobs": 20,
        "options": {"num_predict": 1, "temperature": 0},  # exactly one token
        "messages": [
            {"role": "system", "content": f"Answer with exactly one word: {', '.join(labels)}."},
            {"role": "user", "content": f"{state}\n\nQuestion: {question}"},
        ],
    }
    first_token = _post(payload)["logprobs"][0]
    return label_probabilities(first_token["top_logprobs"], labels)


def yes_no(state: str, question: str) -> float:
    """Probability that the answer is yes."""
    return _ask(state, question, ["yes", "no"])["yes"]


def yes_no_many(state: str, questions: dict[str, str]) -> dict[str, float]:
    """Several yes/no questions about the same state, asked in parallel."""
    with ThreadPoolExecutor() as pool:
        futures = {key: pool.submit(yes_no, state, q) for key, q in questions.items()}
        return {key: future.result() for key, future in futures.items()}


def choice(state: str, question: str, options: list[str]) -> dict[str, float]:
    """Probability for each option. Options are shown as letters so each answer is one token."""
    letters = "abcdefgh"[: len(options)]
    menu = "\n".join(f"{letter}) {option}" for letter, option in zip(letters, options))
    probs = _ask(state, f"{question}\n{menu}", list(letters))
    return {option: probs[letter] for letter, option in zip(letters, options)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all tests in `test_config.py` and `test_system1.py` pass.

- [ ] **Step 5: Write `labs/lab6_system1_basics.py`**

```python
# Lab 6: System 1 basics — a small local model answers typed questions with probabilities.
from common.config import SYSTEM1_MODEL, check_ollama
from common.system1 import choice, yes_no, yes_no_many

CONVERSATION = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""


def main() -> None:
    check_ollama(SYSTEM1_MODEL)
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
    print("\nIntent:", choice("user: Plan me 5 days in Istanbul under $1000", "What does the user want?",
                              ["weather", "packing list", "itinerary"]))

    # 4. The classifier only observes. Plain Python decides.
    decision = "ask the user for the city" if p_city < 0.5 else "go ahead"
    print(f"\nPolicy decision: {decision}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run lab 6**

Run: `ollama pull qwen3.5:4b && uv run labs/lab6_system1_basics.py`
Expected: `P(user named a city)` well below 0.5, `P(args_grounded)` low, `P(missing_info)` high, the intent choice puts most weight on `itinerary`, and the policy line reads `ask the user for the city`.

- [ ] **Step 7: Commit**

```bash
git add labs/common/system1.py labs/lab6_system1_basics.py tests/test_system1.py
git commit -m "Add System 1 helper and lab 6"
```

---

### Task 7: Lab 7 — tool-call gate

**Files:**
- Create: `labs/lab7_tool_call_gate.py`

**Interfaces:**
- Consumes: `common.system1.yes_no_many(state, questions) -> dict[str, float]`; `common.config.MAIN_MODEL, SYSTEM1_MODEL, check_ollama`.

- [ ] **Step 1: Write the lab**

```python
# Lab 7: System 1 gate — check a tool call before it runs; block guessed arguments.
import json

from strands.interventions import Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.config import MAIN_MODEL, SYSTEM1_MODEL, check_ollama
from common.system1 import yes_no_many

# An "eager" assistant that guesses instead of asking — the failure we want to catch.
INSTRUCTIONS = (
    "You are an eager travel assistant. For weather, immediately fetch "
    "https://wttr.in/<city>?format=3 with web_fetch. Never ask for clarification: "
    "if no city is given, assume Seattle."
)

QUESTIONS = {
    "matches_intent": "Does the proposed tool match what the user is asking for?",
    "missing_info": "Is information missing that the tool needs to run correctly?",
    "args_grounded": "Are the tool's argument values based on facts the user actually provided?",
    "premature": "Is it too early to call this tool, before clarifying with the user?",
}


def conversation_text(messages: list[dict]) -> str:
    lines = [f"{m['role']}: {block['text']}" for m in messages for block in m["content"] if "text" in block]
    return "\n".join(lines)


class ToolCallGate(InterventionHandler):
    name = "system1-tool-call-gate"
    YES = 0.65  # the policy knob: what counts as a confident "yes"

    def before_tool_call(self, event):
        call = f"{event.tool_use['name']}({json.dumps(event.tool_use.get('input', {}))})"
        state = f"{conversation_text(event.agent.messages)}\n\nProposed tool call: {call}"
        print(f"\n[gate] model proposes: {call}")

        p = yes_no_many(state, QUESTIONS)  # System 1 observes...
        for name, value in p.items():
            print(f"[gate]   P({name}) = {value:.2f}")

        # ...plain Python decides.
        if p["matches_intent"] < self.YES:
            return Guide(feedback="That tool doesn't match the request. Reconsider.")
        if p["missing_info"] >= self.YES or p["args_grounded"] < self.YES:
            print("[gate] -> Guide: ask the user instead of guessing")
            return Guide(feedback="The arguments look guessed. Ask the user for the missing details.")
        if p["premature"] >= self.YES:
            return Guide(feedback="Too early to call this tool. Clarify with the user first.")
        print("[gate] -> Proceed")
        return Proceed()


def main() -> None:
    check_ollama(MAIN_MODEL, SYSTEM1_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=False,
        interventions=ToolCallGate(),  # NEW: our own System 1 gate
    )
    agent("What's the weather?")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run labs/lab7_tool_call_gate.py`
Expected: `[gate] model proposes: web_fetch({... Seattle ...})`, low `P(args_grounded)`, `[gate] -> Guide: ask the user instead of guessing`, and the final reply asks which city. If the classifier lets the guess through, try `SYSTEM1_MODEL=qwen3.5:9b` and note the result in the commit message; do not change the thresholds to force it.

- [ ] **Step 3: Commit**

```bash
git add labs/lab7_tool_call_gate.py
git commit -m "Add lab 7: System 1 tool-call gate"
```

---

### Task 8: Lab 8 — completion check

**Files:**
- Create: `labs/lab8_completion_check.py`

**Interfaces:**
- Consumes: `common.system1.choice(state, question, options) -> dict[str, float]`; `common.config`.

- [ ] **Step 1: Write the lab**

```python
# Lab 8: System 1 completion check — send the agent back when it stops before the job is done.
from strands.interventions import Guide, InterventionHandler, Proceed
from strands_harness import create_harness

from common.config import MAIN_MODEL, SYSTEM1_MODEL, check_ollama
from common.system1 import choice

# A "lazy" assistant that answers only the first part of a request.
INSTRUCTIONS = (
    "You are a travel assistant. For weather, fetch https://wttr.in/<city>?format=3 with web_fetch. "
    "Answer only the first thing the user asks and then stop."
)


def text_of(message: dict) -> str:
    return "\n".join(block["text"] for block in message["content"] if "text" in block)


class CompletionCheck(InterventionHandler):
    name = "system1-completion-check"
    MAX_GUIDES = 2  # Guide retries the model, so we must cap it

    def __init__(self):
        self.guides = 0

    def after_model_call(self, event):
        response = event.stop_response
        if response is None or response.stop_reason != "end_turn":
            return Proceed()  # only judge final answers, not tool-use turns

        request = text_of(event.agent.messages[0])
        answer = text_of(response.message)
        p = choice(
            f"User request: {request}\n\nAssistant answer: {answer}",
            "How completely does the answer cover everything the user asked for?",
            ["complete", "partial", "not answered"],
        )
        print(f"\n[check] {', '.join(f'P({k})={v:.2f}' for k, v in p.items())}")

        if p["complete"] >= 0.6 or self.guides >= self.MAX_GUIDES:
            print("[check] -> Proceed")
            return Proceed()
        self.guides += 1
        print(f"[check] -> Guide ({self.guides}/{self.MAX_GUIDES}): finish the rest of the request")
        return Guide(feedback="Your answer skipped part of the request. Answer every part the user asked for.")


def main() -> None:
    check_ollama(MAIN_MODEL, SYSTEM1_MODEL)
    agent = create_harness(
        model=MAIN_MODEL,
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=False,
        interventions=CompletionCheck(),  # NEW
    )
    agent("What's the weather in Istanbul, and what should I pack for 4 days there?")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run labs/lab8_completion_check.py`
Expected: first final answer gives only the weather; `[check]` shows `P(complete)` below 0.6 and `-> Guide (1/2)`; the retried answer includes a packing list and the check prints `-> Proceed`. If the model ignores the lazy instruction and answers fully the first time, the check should print `-> Proceed` straight away; in that case strengthen only the INSTRUCTIONS wording.

- [ ] **Step 3: Commit**

```bash
git add labs/lab8_completion_check.py
git commit -m "Add lab 8: System 1 completion check"
```

---

### Task 9: Lab 9 — model switching

**Files:**
- Create: `labs/lab9_model_switching.py`

**Interfaces:**
- Consumes: `common.system1.choice`; `common.config.SMALL_MODEL, BIG_MODEL, SYSTEM1_MODEL, OLLAMA_HOST, check_ollama`.

- [ ] **Step 1: Write the lab**

```python
# Lab 9: System 1 router — easy requests go to a small model, hard ones to a big one.
import asyncio

from strands.models.ollama import OllamaModel
from strands.models.routing import ModelRouter, RoutingCandidate
from strands_harness import create_harness

from common.config import BIG_MODEL, OLLAMA_HOST, SMALL_MODEL, SYSTEM1_MODEL, check_ollama
from common.system1 import choice

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def latest_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message["role"] == "user":
            texts = [block["text"] for block in message["content"] if "text" in block]
            if texts:
                return "\n".join(texts)
    return ""


class System1Strategy:
    """Asks the classifier how hard the request is, then picks a candidate by name."""

    async def select(self, context, **kwargs):
        if context.attempts:
            return None  # a call failed: let the router's default handle it
        request = latest_user_text(context.messages)
        p = await asyncio.to_thread(choice, f"User request: {request}", "How hard is this request?",
                                    ["easy", "hard"])
        pick = "big" if p["hard"] >= 0.5 else "small"
        print(f"\n[router] P(easy)={p['easy']:.2f} P(hard)={p['hard']:.2f} -> {pick}")
        return next(c for c in context.candidates if c.name == pick)


def main() -> None:
    check_ollama(SMALL_MODEL, BIG_MODEL, SYSTEM1_MODEL)
    router = ModelRouter(
        [
            RoutingCandidate(model=OllamaModel(host=OLLAMA_HOST, model_id=SMALL_MODEL), name="small"),
            RoutingCandidate(model=OllamaModel(host=OLLAMA_HOST, model_id=BIG_MODEL), name="big"),
        ],
        strategy=System1Strategy(),
    )
    agent = create_harness(
        model=router,  # NEW: a router instead of one model
        instructions=INSTRUCTIONS,
        builtin_tools=["web_fetch"],
        session=False,
        memory=False,
        skills=False,
    )

    agent("What's the weather in Paris?")
    agent("Plan a 5-day Istanbul itinerary under $1000, with a day trip and where to stay.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run labs/lab9_model_switching.py`
Expected: the first request prints `-> small`, the second `-> big`, and both get answers. If `ModelRouter` rejects a strategy that isn't a subclass, check `strands.models.routing.RoutingStrategy` in the installed package (it is a runtime-checkable Protocol needing only `async select`).

- [ ] **Step 3: Commit**

```bash
git add labs/lab9_model_switching.py
git commit -m "Add lab 9: System 1 model switching"
```

---

### Task 10: README, compile check, GitHub repo, PR

**Files:**
- Create: `README.md`
- Test: `tests/test_labs_compile.py`

- [ ] **Step 1: Write the compile test**

`tests/test_labs_compile.py`:

```python
import py_compile
from pathlib import Path

import pytest

LABS = sorted(Path("labs").glob("lab*.py"))


def test_there_are_nine_labs():
    assert len(LABS) == 9


@pytest.mark.parametrize("lab", LABS, ids=lambda p: p.name)
def test_lab_compiles(lab):
    py_compile.compile(str(lab), doraise=True)
```

Run: `uv run pytest -v` → Expected: all pass.

- [ ] **Step 2: Write `README.md`** in the old repo's format:
  - Title `# Strands Harness Labs` and a one-paragraph intro (Strands Harness SDK + System 1 classifiers, one travel assistant built up lab by lab).
  - `## 🚀 Quick Start`: prerequisites (uv, Ollama); `uv sync`; `cp .env.example .env`; `ollama pull gpt-oss:20b qwen3.5:4b qwen3.5:9b`; the one-line Bedrock switch.
  - `## 📚 Lab Overview`: per lab `### Lab N: Title`, `**File:**`, one-line description, `**What's new:**` (the one `create_harness` argument or class it adds), `**Video:** _coming soon_`, and a `**Run:**` block with the exact command (lab 3 shows both runs; lab 5 shows both parts).
  - `## 🧠 What is a System 1 model?`: 3–4 sentences — Jev, why a classifier returns probabilities, why Python owns the decision, and that this repo uses a small open model on Ollama with token probabilities instead.
  - `## 🆘 Troubleshooting`: Ollama not running; model not pulled; reset state with `rm -rf .agent/sessions .agent/memory trips`; slow first call (model load).
  - `## 🙏 Credits`: Mike Chambers' `mikegc-aws/jev-strands-video` (MIT) for the System 1 pattern, TypeSafe's Jev, the Strands Harness SDK.
  - `## 📄 License`: MIT.

- [ ] **Step 3: Create the private GitHub repo and push**

```bash
git checkout main
gh repo create syedair/strands-harness-labs --private --source . --push
git checkout labs-v1
git push -u origin labs-v1
gh pr create --title "Labs 1-9: Strands Harness + System 1" --body "<summary of labs + test results + per-lab run notes>"
```

- [ ] **Step 4: Final verification**

Run `uv run pytest -v` and every lab once, in order, from a clean state (`rm -rf .agent/sessions .agent/memory trips`). Record in the PR body, per lab, whether the expected behavior appeared.
