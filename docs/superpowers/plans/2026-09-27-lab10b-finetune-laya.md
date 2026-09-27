# Lab 10b: Fine-tune Laya on Travel Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A lab that shows Laya is weak out of the box, then fine-tunes it on Kev-labelled travel questions in about two minutes on a laptop GPU, and measures before/after on lab 10's held-out sets.

**Architecture:** Pure data code (`common/travel_data.py`) builds and labels the training questions; model code (`common/laya_train.py`) holds the training loop adapted from Laya's notebook; `labs/lab10b_finetune_laya.py` runs the four paused steps. The saved model becomes a `laya-travel` System 1 backend and an optional fifth contender in lab 10.

**Tech Stack:** Python 3.13, uv, pytest, PyTorch (MPS / CUDA / CPU), `laya` (optional extra), `huggingface_hub`, `safetensors`, `transformers`.

**Spec:** `docs/specs/2026-09-27-lab10b-finetune-laya-design.md`

## Global Constraints

- Lab 10b's training data must share nothing with lab 10's held-out sets (`BEACH`, `TOOL_CALLS`), and its tool calls must not use a city that appears in `TOOL_CALLS`.
- Training device: `mps`, else `cuda`, else `cpu` with a warning.
- Trained model saved to `models/laya-travel/` (gitignored). Labels cached to `models/laya-travel/labels.json`.
- `TEACHER` env var picks the labeller (default `kev`); `EPOCHS` env var (default 4); `--skip-train` re-runs only the comparison.
- Pauses use `common.show.wait` (no pauses off a terminal or in `--chat`).
- Credit Laya's notebook (Apache-2.0) in `laya_train.py` and the README; the reference copy lives in `docs/reference/laya/`.
- Tests never download a model or train.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Running lab 10b while the teacher can't answer (Kev down, no Jev key): expect the usual one-line fix (or Kev's start offer), not a traceback. Covered by `check_system1(TEACHER)` in Task 4.
2. Re-running after the training questions changed: the label cache must be rebuilt, never reused stale. Test in Task 1.
3. `--skip-train` before any model exists: expect "No fine-tuned model yet. Run it once without --skip-train." Covered in Task 4 (manual check step).
4. `SYSTEM1_MODEL=laya-travel` before training: expect "No fine-tuned Laya yet. Train it with: uv run labs/lab10b_finetune_laya.py". Test in Task 3.
5. Laya not installed: lab 10b prints the install command and exits. Covered in Task 4 via `unavailable("laya")`.

---

### Task 1: Travel training data and teacher labels

**Files:**
- Modify: `labs/common/showdown.py` (add the three question constants)
- Modify: `labs/lab10_system1_showdown.py` (use them in `ROUNDS`)
- Create: `labs/common/travel_data.py`
- Test: `tests/test_travel_data.py`

**Interfaces:**
- Produces: `showdown.BEACH_Q`, `showdown.ABSTRACT_Q`, `showdown.CONCRETE_Q` (str)
- Produces: `travel_data.training_questions(seed: int = 7, n_calls: int = 300) -> list[tuple[str, str]]` — `(state, question)` pairs
- Produces: `travel_data.label(pairs, teacher: str, cache: Path, ask=yes_no) -> list[dict]` — rows `{"state", "question", "p"}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_travel_data.py
import json
import re

from common import travel_data
from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS

HELD_OUT_CITIES = {m for s in TOOL_CALLS for m in re.findall(r"wttr\.in/(\w+)", s)}


def test_training_questions_share_nothing_with_lab_10():
    pairs = travel_data.training_questions()
    states = {s for s, _ in pairs}
    assert not states & set(BEACH) and not states & set(TOOL_CALLS)
    for state, question in pairs:
        if question != BEACH_Q:
            assert re.search(r"wttr\.in/(\w+)", state).group(1) not in HELD_OUT_CITIES


def test_every_tool_call_is_asked_both_ways_and_covers_all_three_kinds():
    pairs = travel_data.training_questions()
    calls = [s for s, q in pairs if q == ABSTRACT_Q]
    assert sorted(calls) == sorted(s for s, q in pairs if q == CONCRETE_Q)
    kinds = set()
    for call in calls:
        user, city = re.match(r"user: (.*)\n\nProposed tool call: .*wttr\.in/(\w+)", call).groups()
        named = [c for c in travel_data.CITIES if c in user]
        kinds.add("given" if city in named else "different" if named else "none")
    assert kinds == {"given", "different", "none"}


def test_label_asks_the_teacher_and_caches(tmp_path):
    asked = []
    ask = lambda state, question, model=None: asked.append(model) or 0.25
    pairs = [("Boracay", BEACH_Q), ("Madrid", BEACH_Q)]
    rows = travel_data.label(pairs, "kev", tmp_path / "labels.json", ask=ask)
    assert rows == [{"state": "Boracay", "question": BEACH_Q, "p": 0.25},
                    {"state": "Madrid", "question": BEACH_Q, "p": 0.25}]
    assert asked == ["kev", "kev"]
    again = travel_data.label(pairs, "kev", tmp_path / "labels.json", ask=lambda *a, **k: 1 / 0)
    assert again == rows  # cached: the teacher isn't asked again


def test_label_cache_is_rebuilt_when_questions_or_teacher_change(tmp_path):
    cache = tmp_path / "labels.json"
    travel_data.label([("Boracay", BEACH_Q)], "kev", cache, ask=lambda *a, **k: 0.9)
    rows = travel_data.label([("Madrid", BEACH_Q)], "kev", cache, ask=lambda *a, **k: 0.1)
    assert rows[0]["state"] == "Madrid" and rows[0]["p"] == 0.1
    rows = travel_data.label([("Madrid", BEACH_Q)], "jev", cache, ask=lambda *a, **k: 0.2)
    assert rows[0]["p"] == 0.2 and json.loads(cache.read_text())["teacher"] == "jev"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --inexact pytest tests/test_travel_data.py -q`
Expected: FAIL — `ImportError: cannot import name 'ABSTRACT_Q'` / `No module named 'common.travel_data'`

- [ ] **Step 3: Add the question constants and use them in lab 10**

In `labs/common/showdown.py`, just above `def _call(`:

```python
# Lab 10's three questions (lab 10b trains on them too, with different examples).
BEACH_Q = "Is this primarily a beach or tropical holiday destination?"
ABSTRACT_Q = "Are the tool's argument values based on facts the user actually provided?"
CONCRETE_Q = "Did the user mention the same city that the tool call uses?"
```

In `labs/lab10_system1_showdown.py`, replace the `ROUNDS` block and the import:

```python
from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS, contenders, score

ROUNDS = [
    ("Beach destinations", BEACH, BEACH_Q),
    # The same tool calls, asked two ways: small models need concrete questions.
    ("Tool calls, abstract question", TOOL_CALLS, ABSTRACT_Q),
    ("Tool calls, concrete question", TOOL_CALLS, CONCRETE_Q),
]
```

- [ ] **Step 4: Write `labs/common/travel_data.py`**

```python
# Lab 10b's training data: travel questions that share nothing with lab 10's held-out sets, labelled by a teacher.
import itertools
import json
import random
from pathlib import Path

from common.showdown import ABSTRACT_Q, BEACH, BEACH_Q, CONCRETE_Q, TOOL_CALLS, _call
from common.system1 import yes_no

# New destinations for the beach question: beach getaways, inland and mountain cities, coastal cities.
PLACES = [
    "Boracay", "Langkawi", "Koh Samui", "Krabi", "Bora Bora", "Tahiti", "Aruba", "Barbados", "Punta Cana",
    "Montego Bay", "Nassau", "Tulum", "Playa del Carmen", "Cabo San Lucas", "Maui", "Waikiki", "Gold Coast",
    "Byron Bay", "Cairns", "Mykonos", "Santorini", "Ibiza", "Mallorca", "Tenerife", "Gran Canaria", "Crete",
    "Rhodes", "Antalya", "Bodrum", "Hurghada", "Sharm El Sheikh", "Mombasa", "Diani Beach", "Praslin", "Lombok",
    "Gili Islands", "Palawan", "Cebu", "Nha Trang", "Da Nang", "Mirissa", "Varkala", "Andaman Islands",
    "Fort Lauderdale", "Key West", "San Juan", "Curaçao", "St Lucia", "Antigua", "Florianópolis",
    "Salvador de Bahia", "Punta del Este", "Copacabana", "Jeffreys Bay", "Zakynthos", "Sardinia", "Corsica",
    "Lagos (Algarve)", "Madrid", "Budapest", "Warsaw", "Krakow", "Brussels", "Amsterdam", "Stockholm", "Oslo",
    "Helsinki", "Copenhagen", "Dublin", "Edinburgh", "Florence", "Milan", "Salzburg", "Bern", "Lucerne",
    "Interlaken", "St. Moritz", "Banff", "Whistler", "Denver", "Salt Lake City", "Las Vegas", "Phoenix",
    "Mexico City", "Bogotá", "Quito", "La Paz", "Cusco", "Santiago", "Buenos Aires", "Marrakech", "Cairo",
    "Nairobi", "Addis Ababa", "Johannesburg", "Delhi", "Jaipur", "Agra", "Varanasi", "Lhasa", "Ulaanbaatar",
    "Almaty", "Tbilisi", "Yerevan", "Tehran", "Riyadh", "Amman", "Jerusalem", "Xi'an", "Chengdu", "Shanghai",
    "Osaka", "Sapporo", "Busan", "Taipei", "Hong Kong", "Hanoi", "Bangkok", "Kuala Lumpur", "Jakarta", "Manila",
    "Mumbai", "Chennai", "Kolkata", "Athens", "Naples", "Venice", "Genoa", "Marseille", "Bordeaux", "Porto",
    "Valencia", "Seville", "Hamburg", "Gdansk", "Tallinn", "Riga", "Vilnius", "St. Petersburg", "Vladivostok",
    "Vancouver", "San Francisco", "Los Angeles", "Boston", "Montreal", "Quebec City", "Halifax", "Auckland",
    "Wellington", "Melbourne", "Perth", "Hobart", "Dakar", "Accra", "Casablanca", "Tunis", "Alexandria",
]

# Tool calls: cities that never appear in lab 10's held-out tool calls.
CITIES = ["Madrid", "Riga", "Oslo", "Lima", "Cairo", "Delhi", "Bangkok", "Sydney", "Toronto", "Athens",
          "Vienna", "Lisbon", "Nairobi", "Seoul", "Denver", "Dublin", "Hanoi", "Doha", "Milan", "Porto"]
WITH_CITY = ["What's the weather in {c}?", "How's the weather in {c} today?", "Is it cold in {c}?",
             "I'm heading to {c} next week, what's it like there?", "Forecast for {c} please",
             "Do I need a coat in {c}?", "I live in {c}. Is it raining at home?", "Is {c} sunny right now?",
             "Flying to {c} tomorrow. Will it rain?", "What should I wear in {c} this weekend?"]
NO_CITY = ["What's it like outside?", "Will it rain later?", "Do I need sunscreen today?", "How cold is it?",
           "What's the forecast for tomorrow?", "Should I bring an umbrella?", "Is it windy today?",
           "What should I wear today?", "Any storms coming?", "What's the temperature right now?"]


def tool_calls(seed: int = 7, n: int = 300) -> list[str]:
    """Weather tool calls where the city was given, was a different one, or was never mentioned (a guess)."""
    rng = random.Random(seed)
    calls = set()
    for tpl, city in itertools.product(WITH_CITY, CITIES):
        calls.add(_call(tpl.format(c=city), city))  # the user's city
        calls.add(_call(tpl.format(c=city), rng.choice([c for c in CITIES if c != city])))  # a different one
    for tpl in NO_CITY:
        for city in rng.sample(CITIES, 6):
            calls.add(_call(tpl, city))  # no city given: a guess
    return rng.sample(sorted(calls - set(TOOL_CALLS)), n)


def training_questions(seed: int = 7, n_calls: int = 300) -> list[tuple[str, str]]:
    """(state, question) pairs: every new destination asked the beach question, every tool call asked both ways."""
    places = [p for p in PLACES if p not in BEACH]
    calls = tool_calls(seed, n_calls)
    return [(p, BEACH_Q) for p in places] + [(s, q) for s in calls for q in (ABSTRACT_Q, CONCRETE_Q)]


def label(pairs: list[tuple[str, str]], teacher: str, cache: Path, ask=yes_no) -> list[dict]:
    """The teacher's probability for each question. Cached: the same questions and teacher skip the teacher."""
    wanted = [[s, q] for s, q in pairs]
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved["teacher"] == teacher and [[r["state"], r["question"]] for r in saved["rows"]] == wanted:
            return saved["rows"]
    rows = [{"state": s, "question": q, "p": ask(s, q, model=teacher)} for s, q in pairs]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"teacher": teacher, "rows": rows}, indent=1))
    return rows
```

- [ ] **Step 5: Run the new tests and the full suite**

Run: `uv run --inexact pytest tests/test_travel_data.py -q && uv run --inexact pytest -q`
Expected: 4 passed; full suite all passed

- [ ] **Step 6: Commit**

```bash
git add labs/common/showdown.py labs/lab10_system1_showdown.py labs/common/travel_data.py tests/test_travel_data.py
git commit -m "Lab 10b: travel training data that shares nothing with lab 10, labelled and cached by a teacher"
```

---

### Task 2: The training loop

**Files:**
- Create: `labs/common/laya_train.py`
- Test: `tests/test_laya_train.py`

**Interfaces:**
- Consumes: rows from `travel_data.label` (`{"state", "question", "p"}`)
- Produces: `laya_train.pick_device() -> str` (`"mps" | "cuda" | "cpu"`)
- Produces: `laya_train.base_model_dir() -> str` (downloads `convaiinnovations/laya` once)
- Produces: `laya_train.fit_temperature(logits: torch.Tensor, targets: torch.Tensor) -> float`
- Produces: `laya_train.train(rows: list[dict], out_dir: Path, epochs: int, device: str, log=print) -> dict` with keys `seconds`, `peak_gb` (float or None), `temperature`, `items`
- Produces: `laya_train.asker(agent) -> Callable[[str, str], float]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_laya_train.py
import pytest

torch = pytest.importorskip("torch")  # the laya extra brings torch
from common import laya_train  # noqa: E402


def test_device_prefers_apple_gpu_then_nvidia_then_cpu(monkeypatch):
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert laya_train.pick_device() == "mps"
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert laya_train.pick_device() == "cuda"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert laya_train.pick_device() == "cpu"


def test_temperature_softens_an_overconfident_model():
    logits = torch.tensor([[0.0, 4.0]] * 50)  # says yes at ~0.98
    targets = torch.tensor([[0.3, 0.7]] * 50)  # the teacher said 0.7
    assert laya_train.fit_temperature(logits, targets) > 1.5


def test_temperature_leaves_a_calibrated_model_alone():
    logits = torch.tensor([[0.0, 0.8473]] * 50)  # softmax -> 0.7
    targets = torch.tensor([[0.3, 0.7]] * 50)
    assert laya_train.fit_temperature(logits, targets) == pytest.approx(1.0, abs=0.05)


def test_asker_returns_the_yes_probability():
    class FakeAgent:
        def predict(self, state, questions):
            assert questions == {"q": {"type": "noul", "instructions": "Beach?"}}
            return {"answers": {"q": {"noul": 0.83}}}

    assert laya_train.asker(FakeAgent())("Boracay", "Beach?") == 0.83
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --inexact pytest tests/test_laya_train.py -q`
Expected: FAIL — `No module named 'common.laya_train'`

- [ ] **Step 3: Write `labs/common/laya_train.py`**

```python
"""Fine-tune Laya on labelled yes/no questions.

Adapted from Laya's own notebook (docs/reference/laya/, Apache-2.0, github.com/NandhaKishorM/laya): the same
proper-scoring-rule rewards plus soft cross-entropy, on one GPU instead of two NVIDIA T4s, in full precision,
for yes/no questions only. Then one calibration temperature, fitted on a held-out slice like the notebook does.
"""
import json
import os
import random
import time
from pathlib import Path

import torch

BASE = "convaiinnovations/laya"  # the 421M-parameter base checkpoint
MICRO, ACCUM, GROUP = 8, 4, 4  # 8 questions per step, an update every 4 steps, 4 noisy samples per question
SIGMA_START, SIGMA_END = 0.4, 0.1  # exploration noise, shrinking over the epochs


def pick_device() -> str:
    """Apple GPU, else NVIDIA GPU, else CPU (slow)."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def base_model_dir() -> str:
    """Download the base checkpoint once (Hugging Face caches it) and return its folder."""
    from huggingface_hub import snapshot_download
    from laya.agent import _fix_tokenizer_config

    path = snapshot_download(BASE)
    _fix_tokenizer_config(path)
    return path


def asker(agent):
    """ask(state, question) -> P(yes), for a loaded laya.Agent."""
    def ask(state: str, question: str) -> float:
        answers = agent.predict(state, {"q": {"type": "noul", "instructions": question}})["answers"]
        return float(answers["q"]["noul"])
    return ask


def fit_temperature(logits: torch.Tensor, targets: torch.Tensor) -> float:
    """The one number that makes the model's probabilities match the teacher's on held-out questions."""
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = -(targets * torch.log_softmax(logits / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss

    opt.step(closure)
    return float(torch.clamp(log_t.exp(), 0.1, 10.0))


def _items(rows, tok, cfg):
    """Tokenize each labelled question the way Laya reads it; the target is [P(no), P(yes)] from the teacher."""
    from laya.common import QTYPES, build_sequence, render_options

    items = []
    for row in rows:
        q = {"t": "noul", "ins": row["question"], "crit": {}}
        seq, markers = build_sequence(tok, row["state"], q, cfg["max_len"], cfg["head_max_len"])
        if len(markers) == len(render_options(q)):
            items.append({"ids": seq, "markers": markers, "qtype": QTYPES["noul"], "target": [1 - row["p"], row["p"]]})
    return items


def _batch(items, pad_id, device):
    n, length = len(items), max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, length), pad_id, dtype=torch.long)
    att = torch.zeros((n, length), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax))
    for i, it in enumerate(items):
        ids[i, :len(it["ids"])] = torch.tensor(it["ids"])
        att[i, :len(it["ids"])] = 1
        mpos[i, :len(it["markers"])] = torch.tensor(it["markers"])
        mmask[i, :len(it["markers"])] = True
        target[i, :len(it["target"])] = torch.tensor(it["target"])
    qtype = torch.tensor([it["qtype"] for it in items])
    return [t.to(device) for t in (ids, att, mpos, mmask, target, qtype)]


def _peak_gb(device: str) -> float | None:
    if device == "mps":
        return torch.mps.driver_allocated_memory() / 1e9
    if device == "cuda":
        return torch.cuda.max_memory_allocated() / 1e9
    return None


def train(rows: list[dict], out_dir: Path, epochs: int, device: str, log=print) -> dict:
    """Fine-tune the base checkpoint on the labelled rows and save it to out_dir."""
    from laya.common import build_model, proper_reward
    from safetensors.torch import load_file, save_file
    from transformers import AutoTokenizer

    base = base_model_dir()
    tok = AutoTokenizer.from_pretrained(os.path.join(base, "tokenizer"))
    cfg = json.load(open(os.path.join(base, "rl_agent_config.json")))
    items = _items(rows, tok, cfg)
    random.Random(20260922).shuffle(items)
    n_calib = max(40, len(items) // 10)  # held out: calibration is fitted on questions it never trained on
    calib, train_items = items[:n_calib], items[n_calib:]

    model = build_model(cfg, encoder_dir=os.path.join(base, "encoder"))
    model.load_state_dict(load_file(os.path.join(base, "model.safetensors")), strict=True)
    model.to(device).train()
    enc = [p for n, p in model.named_parameters() if "encoder." in n]
    head = [p for n, p in model.named_parameters() if "encoder." not in n]
    opt = torch.optim.AdamW([{"params": enc, "lr": 2.5e-5}, {"params": head, "lr": 1e-4}], weight_decay=0.01)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=max(1, len(train_items) // (MICRO * ACCUM) * epochs), eta_min=1e-6)

    start = time.time()
    for epoch in range(epochs):
        random.Random(42 + epoch).shuffle(train_items)
        sigma = SIGMA_START + (SIGMA_END - SIGMA_START) * epoch / max(1, epochs - 1)
        total, steps = 0.0, 0
        opt.zero_grad(set_to_none=True)
        for b in range(0, len(train_items), MICRO):
            ids, att, mpos, mmask, target, qtype = _batch(train_items[b:b + MICRO], tok.pad_token_id, device)
            logits, act = model(ids, att, mpos, mmask, qtype)
            logits = logits.float()
            # Try a few noisy versions of the answer, reward the ones a proper scoring rule likes...
            k = mmask.sum(-1, keepdim=True).float()
            eps = torch.randn((GROUP,) + logits.shape, device=device) * sigma * mmask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mmask
            z = logits.detach().unsqueeze(0) + eps
            with torch.no_grad():
                reward = proper_reward(torch.softmax(z.masked_fill(~mmask, -1e4), -1), target.unsqueeze(0), qtype,
                                       mmask, w_sph=0.75, w_rps=1.0)
                adv = reward - reward.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mmask).sum(-1) / (2 * sigma ** 2)
            # ...and pull the answer towards the teacher's probabilities.
            copy_teacher = -(target * torch.log_softmax(logits.masked_fill(~mmask, -1e4), -1)).sum(-1).mean()
            loss = -(adv * logp).mean() + copy_teacher
            (loss / ACCUM + 0.0 * act.sum()).backward()
            steps += 1
            if steps % ACCUM == 0 or b + MICRO >= len(train_items):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
            total += loss.item()
        log(f"    epoch {epoch + 1}/{epochs}: loss {total / steps:.3f}   ({time.time() - start:.0f}s)")
    seconds, peak = time.time() - start, _peak_gb(device)

    model.eval()
    zs, ts = [], []
    with torch.no_grad():
        for b in range(0, len(calib), 16):
            ids, att, mpos, mmask, target, qtype = _batch(calib[b:b + 16], tok.pad_token_id, device)
            zs.append(model(ids, att, mpos, mmask, qtype)[0].float().cpu()[:, :2])
            ts.append(target.cpu()[:, :2])
    temperature = fit_temperature(torch.cat(zs), torch.cat(ts))

    out_dir.mkdir(parents=True, exist_ok=True)
    save_file({k: v.half().contiguous().cpu() for k, v in model.state_dict().items()}, str(out_dir / "model.safetensors"))
    model.encoder.config.save_pretrained(str(out_dir / "encoder"))
    tok.save_pretrained(str(out_dir / "tokenizer"))
    from laya.common import QTYPES
    temps = cfg.get("temperature", [1.2, 1.2, 1.2])
    temps = list(temps) if isinstance(temps, list) else [temps] * 3
    temps[QTYPES["noul"]] = temperature
    cfg.update(fine_tuned=True, model_name="laya-travel", temperature=temps)
    cfg.pop("temperature_by_options", None)  # old per-bucket values would override the new fit
    (out_dir / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    return {"seconds": seconds, "peak_gb": peak, "temperature": temperature, "items": len(train_items)}
```

- [ ] **Step 4: Run the tests and the full suite**

Run: `uv run --inexact pytest tests/test_laya_train.py -q && uv run --inexact pytest -q`
Expected: 4 passed; full suite all passed

- [ ] **Step 5: Commit**

```bash
git add labs/common/laya_train.py tests/test_laya_train.py
git commit -m "Lab 10b: Laya's fine-tuning loop on one GPU (adapted from its Apache-2.0 notebook)"
```

---

### Task 3: The `laya-travel` backend and the fifth contender

**Files:**
- Modify: `labs/common/config.py` (add `LAYA_TRAVEL_DIR`)
- Modify: `labs/common/system1.py` (`_backend`, `unavailable`, `display_name`, `_typed_answers`, `_quiet_laya`, `_laya_travel`)
- Modify: `labs/common/showdown.py` (`CONTENDERS`, `fine_tuned_ready`, `contenders`)
- Modify: `.gitignore` (add `models/`)
- Test: `tests/test_system1.py`, `tests/test_showdown.py`

**Interfaces:**
- Produces: `config.LAYA_TRAVEL_DIR: Path` (= repo root / `models` / `laya-travel`)
- Produces: `SYSTEM1_MODEL=laya-travel` works with `yes_no`, `yes_no_many`, `choice`, `unavailable`, `display_name`
- Produces: `showdown.fine_tuned_ready() -> bool`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_system1.py`:

```python
def test_laya_travel_before_training_says_how_to_make_it(monkeypatch, tmp_path):
    monkeypatch.setattr(system1.config, "LAYA_TRAVEL_DIR", tmp_path / "nothing-here")
    monkeypatch.setattr(system1, "_laya_router", lambda: object())  # Laya itself is installed
    assert system1.unavailable("laya-travel") == (
        "No fine-tuned Laya yet. Train it with: uv run labs/lab10b_finetune_laya.py")


def test_laya_travel_is_named_and_answers_through_its_own_agent(monkeypatch):
    class FakeAgent:
        def predict(self, state, questions):
            return {"answers": {k: {"noul": 0.9} for k in questions}}

    monkeypatch.setattr(system1, "_laya_travel", lambda: FakeAgent())
    assert system1.display_name("laya-travel") == "Laya (fine-tuned on travel)"
    assert system1.yes_no("user: hi", "Greeting?", model="laya-travel") == 0.9
```

Append to `tests/test_showdown.py`:

```python
def test_the_fine_tuned_contender_joins_only_once_it_exists(monkeypatch):
    monkeypatch.setattr(showdown, "unavailable", lambda model: None)
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)
    assert "laya-travel (fine-tuned)" not in [n for n, _ in showdown.contenders()]
    monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: True)
    assert [n for n, _ in showdown.contenders()][-1] == "laya-travel (fine-tuned)"
```

In the same file, make the three existing contender tests independent of whether a model has been trained on this machine: add `monkeypatch.setattr(showdown, "fine_tuned_ready", lambda: False)` as the first line of `test_unavailable_contenders_are_skipped_with_reason`, `test_all_contenders_when_available` and `test_contender_asks_its_own_backend`.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --inexact pytest tests/test_system1.py tests/test_showdown.py -q`
Expected: FAIL — `ValueError: SYSTEM1_MODEL 'laya-travel' must be ...` and `AttributeError: ... fine_tuned_ready`

- [ ] **Step 3: Implement**

`labs/common/config.py` — add `from pathlib import Path` to the imports and, after `KEV_URL`:

```python
# Where lab 10b saves the fine-tuned Laya (gitignored).
LAYA_TRAVEL_DIR = Path(__file__).resolve().parents[2] / "models" / "laya-travel"
```

`labs/common/system1.py`:
- In the header comment, add the line `#   laya-travel    Laya fine-tuned on travel questions by lab 10b`.
- In `_backend`, change `if model in ("jev", "kev", "laya"):` to `if model in ("jev", "kev", "laya", "laya-travel"):` and the error text to `"...must be ollama/<name>, jev, kev, laya or laya-travel"`.
- In `unavailable`, after the `laya` check:

```python
    if backend == "laya-travel":
        if _laya_router() is None:
            return "Laya isn't installed. Run: uv sync --extra laya --inexact"
        if not (config.LAYA_TRAVEL_DIR / "model.safetensors").exists():
            return "No fine-tuned Laya yet. Train it with: uv run labs/lab10b_finetune_laya.py"
```

- In `display_name`, first line after resolving the backend:

```python
    if backend == "laya-travel":
        return "Laya (fine-tuned on travel)"
```

- In `_typed_answers`, first:

```python
    if backend == "laya-travel":
        return _laya_travel().predict(state, questions)["answers"]
```

- Replace `_laya_router` with a shared quiet setup plus the new cached loader:

```python
def _quiet_laya() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")  # quiet the model download check
    # Laya warns that its confidence values are uncalibrated; we only use its probabilities.
    warnings.filterwarnings("ignore", message="laya: this checkpoint")


@functools.cache
def _laya_router():
    _quiet_laya()
    try:
        from laya import Router
    except ImportError:
        return None
    return Router()


@functools.cache
def _laya_travel():
    """Lab 10b's fine-tuned Laya, loaded once."""
    _quiet_laya()
    import laya

    return laya.Agent(str(config.LAYA_TRAVEL_DIR))
```

`labs/common/showdown.py` — add `from common import config` to the imports, then:

```python
CONTENDERS = [
    ("jev (paid)", "jev"),
    ("kev-4b (open)", "kev"),
    ("laya (open)", "laya"),
    ("qwen3.5 (stand-in)", "ollama/qwen3.5:4b"),
    ("laya-travel (fine-tuned)", "laya-travel"),  # only after lab 10b has trained it
]


def fine_tuned_ready() -> bool:
    """Has lab 10b saved a fine-tuned Laya on this machine?"""
    return (config.LAYA_TRAVEL_DIR / "model.safetensors").exists()
```

and in `contenders()`, first line inside the loop:

```python
        if model == "laya-travel" and not fine_tuned_ready():
            continue  # not trained yet: lab 10b makes it
```

`.gitignore` — add a line `models/`.

- [ ] **Step 4: Run the tests and the full suite**

Run: `uv run --inexact pytest tests/test_system1.py tests/test_showdown.py -q && uv run --inexact pytest -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add labs/common/config.py labs/common/system1.py labs/common/showdown.py .gitignore tests/test_system1.py tests/test_showdown.py
git commit -m "SYSTEM1_MODEL=laya-travel, and lab 10 adds the fine-tuned Laya once it exists"
```

---

### Task 4: `labs/lab10b_finetune_laya.py`

**Files:**
- Create: `labs/lab10b_finetune_laya.py`
- Modify: `tests/test_labs_compile.py` (14 → 15 lab files)

**Interfaces:**
- Consumes: `travel_data.training_questions`, `travel_data.label`, `laya_train.pick_device`, `laya_train.base_model_dir`, `laya_train.train`, `laya_train.asker`, `lab10_system1_showdown.ROUNDS`, `lab10_system1_showdown.verdict`, `common.show.brier_row`, `common.show.wait`, `common.system1.check_system1 / display_name / unavailable / yes_no`, `config.LAYA_TRAVEL_DIR`, `showdown.score`

- [ ] **Step 1: Update the compile test (it fails until the file exists)**

In `tests/test_labs_compile.py`:

```python
def test_there_are_fifteen_lab_files():
    assert len(LABS) == 15  # lab 6 is split into 6a-6e, lab 10 has a 10b (lab 11 lives in lab11/)
```

Run: `uv run --inexact pytest tests/test_labs_compile.py -q`
Expected: FAIL — `assert 14 == 15`

- [ ] **Step 2: Write the lab**

```python
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
from common.system1 import check_system1, display_name, unavailable, yes_no
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
    problem = unavailable("laya")
    if problem:
        print(problem)
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
            print(f"    {state.splitlines()[-1][:80]}  →  {question}")
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
```

- [ ] **Step 3: Run the tests**

Run: `uv run --inexact pytest -q`
Expected: all passed (including `test_there_are_fifteen_lab_files` and `test_lab_compiles[lab10b_finetune_laya.py]`)

- [ ] **Step 4: Run it for real (Kev running, Apple GPU)**

Run: `uv run --inexact labs/lab10b_finetune_laya.py </dev/null`
Expected: step 1 prints ~764 questions; step 2 labels them (~90 s; instant on a re-run); step 3 prints 4 epochs, time and peak memory; step 4 shows three rounds where `laya (fine-tuned)` beats `laya (base)` on both tool-call rounds (spike: 0.230 → 0.019 concrete, 0.240 → 0.111 abstract). Record the numbers for the README.

Then: `uv run --inexact labs/lab10b_finetune_laya.py --skip-train </dev/null` — expected: straight to step 4.
Then: `uv run --inexact labs/lab10_system1_showdown.py </dev/null` — expected: a fifth row `laya-travel (fine-tuned)`.
Then: `SYSTEM1_MODEL=laya-travel uv run --inexact labs/lab7_tool_call_gate.py </dev/null` — expected: `System 1: Laya (fine-tuned on travel)`, and the Seattle guess is still blocked.

- [ ] **Step 5: Commit**

```bash
git add labs/lab10b_finetune_laya.py tests/test_labs_compile.py
git commit -m "Lab 10b: fine-tune Laya on Kev-labelled travel questions, then re-run lab 10's rounds"
```

---

### Task 5: README, diagram and script

**Files:**
- Modify: `README.md` (lab list, a Lab 10b section, credits)
- Modify: `docs/diagrams/make_diagrams.py` (local, uncommitted: a `lab10b-finetune-laya` diagram)
- Modify: `docs/video/script.md` (local, uncommitted: a Lab 10b section)

- [ ] **Step 1: README Lab 10b section** (after the Lab 10 section), using the numbers recorded in Task 4 Step 4:

```markdown
### Lab 10b: Fine-tune Laya on Travel Data
**File:** `labs/lab10b_finetune_laya.py`
Laya is the fastest System 1 model here and the weakest out of the box. Its own docs say to treat it as a fast base
to specialise. So we do: Kev labels a few hundred travel questions, Laya learns from Kev's probabilities
(distillation), and we re-run lab 10's rounds on questions it never trained on.
**What's new:** fine-tuning a System 1 model on your own data; `SYSTEM1_MODEL=laya-travel` to use it in labs 6e–9
**Needs:** `uv sync --extra laya --inexact`; a teacher (Kev running, or `TEACHER=jev` with `TYPESAFE_API_KEY`)

| Hardware | Status |
|---|---|
| Apple M4 Max (51 GB), Apple GPU | measured: ~2 min training, 10.8 GB peak |
| Apple Silicon with 16 GB+ | should work (not measured) |
| NVIDIA GPU with 12 GB+ | should work (not measured) |
| CPU only | works, slowly (not measured) |

Results, measured on an M4 Max (Brier · accuracy on lab 10's held-out questions):

| Round | Base Laya | Fine-tuned Laya | Kev (teacher) |
|---|---|---|---|
| <fill from the Task 4 run> | | | |

The recipe is Laya's own: its fine-tuning notebook is in `docs/reference/laya/` (Apache-2.0), with notes on how
lab 10b differs.
**Video:** _coming soon_
**Run:** `uv run labs/lab10b_finetune_laya.py` (then `--skip-train` to only compare)
```

Also add Lab 10b to the README's list of labs, and to Credits: `- [Laya](https://github.com/NandhaKishorM/laya) (Apache-2.0): lab 10b adapts its fine-tuning notebook (copy in docs/reference/laya/).`

- [ ] **Step 2: Diagram** — in `docs/diagrams/make_diagrams.py`, after lab 10, add a `lab10b-finetune-laya` diagram built with `lab(...)` (idea line: "Laya isn't great out of the box. Two minutes of training on your laptop fixes that."): nodes Travel questions → Kev (teacher) → labels → Laya training (GPU) → fine-tuned Laya; a `bars` chart of base vs fine-tuned Brier per round from the Task 4 run with `threshold=(0.25, "coin flip")`; a note with the hardware line. Build and render:

Run: `uv run --with fonttools --with brotli --with playwright python docs/diagrams/make_diagrams.py && uv run --with playwright python ~/.claude/skills/excalidraw-diagrams/scripts/render.py docs/diagrams/lab10b-finetune-laya.excalidraw`
Expected: `0 layout problem(s) in total`

- [ ] **Step 3: Script** — in `docs/video/script.md`, after Lab 10, a Lab 10b section in the same short-sentence style: Laya is fast but weak; show the reference notebook; "we don't label by hand, Kev does"; run the four steps; read the before/after numbers; the hardware line.

- [ ] **Step 4: Commit the README**

```bash
git add README.md
git commit -m "README: lab 10b, hardware, results and credit to Laya's notebook"
```
