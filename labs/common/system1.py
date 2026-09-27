# System 1: a classifier answers narrow, typed questions with probabilities.
# It never decides anything — your Python code does.
#
# SYSTEM1_MODEL picks who answers:
#   ollama/<name>  a small local chat model as a stand-in (one token + its logprobs)
#   jev            TypeSafe's hosted System 1 model (TYPESAFE_API_KEY)
#   kev            an open Jev-alike served on your machine (KEV_URL)
#   laya           an open, BERT-based System 1 model (uv sync --extra laya --inexact)
#   laya-travel    Laya fine-tuned on travel questions by lab 10b
import functools
import importlib.util
import math
import os
import subprocess
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from common import config

JEV_URL = "https://api.typesafe.ai/v1/systemone"
_LAYA_LOCK = threading.Lock()
KEV_SCRIPT = Path(__file__).resolve().parents[2] / "kev.sh"


def yes_no(state: str, question: str, model: str | None = None) -> float:
    """Probability that the answer is yes."""
    return yes_no_many(state, {"q": question}, model)["q"]


def yes_no_many(state: str, questions: dict[str, str], model: str | None = None) -> dict[str, float]:
    """Several yes/no questions about the same state."""
    backend, name = _backend(model)
    if backend == "ollama":
        with ThreadPoolExecutor() as pool:  # one request per question, in parallel
            futures = {key: pool.submit(_ollama_ask, name, state, q, ["yes", "no"]) for key, q in questions.items()}
            return {key: future.result()["yes"] for key, future in futures.items()}
    typed = {key: {"type": "noul", "instructions": q} for key, q in questions.items()}
    answers = _typed_answers(backend, state, typed)  # real System 1 models: one request
    return {key: float(answers[key]["noul"]) for key in questions}


def choice(state: str, question: str, options: list[str], model: str | None = None) -> dict[str, float]:
    """Probability for each option."""
    backend, name = _backend(model)
    if backend == "ollama":
        letters = "abcdefgh"[: len(options)]  # letters keep each answer to one token
        menu = "\n".join(f"{letter}) {option}" for letter, option in zip(letters, options))
        probs = _ollama_ask(name, state, f"{question}\n{menu}", list(letters))
        return {option: probs[letter] for letter, option in zip(letters, options)}
    typed = {"q": {"type": "choice", "instructions": question, "criteria": {o: o for o in options}}}
    probs = _typed_answers(backend, state, typed)["q"]["probabilities"]
    return {option: float(probs[option]) for option in options}


def unavailable(model: str | None = None) -> str | None:
    """Why this classifier can't run here (with the fix), or None if it can."""
    backend, name = _backend(model)
    if backend == "jev" and not os.environ.get("TYPESAFE_API_KEY"):
        return "Jev needs TYPESAFE_API_KEY (get one at typesafe.ai)"
    if backend == "kev" and not _kev_up():
        return f"Kev isn't running on {config.KEV_URL}. Start it with: ./kev.sh start"
    if backend == "laya" and _laya_router() is None:
        return "Laya isn't installed. Run: uv sync --extra laya --inexact"
    if backend == "laya-travel":
        if not laya_installed():
            return "Laya isn't installed. Run: uv sync --extra laya --inexact"
        if not (config.LAYA_TRAVEL_DIR / "model.safetensors").exists():
            return "No fine-tuned Laya yet. Train it with: uv run labs/lab10b_finetune_laya.py"
    if backend == "ollama":
        try:
            pulled = config._pulled_models()
        except httpx.HTTPError:
            return f"Ollama isn't reachable at {config.OLLAMA_HOST}. Start it with: ollama serve"
        if name not in pulled and f"{name}:latest" not in pulled:
            return f"Model {name} isn't pulled. Run: ollama pull {name}"
    return None


def display_name(model: str | None = None) -> str:
    """How to say which System 1 model is answering, e.g. "Kev" or "Qwen stand-in (qwen3.5:4b)"."""
    backend, name = _backend(model or config.SYSTEM1_MODEL)
    if backend == "laya-travel":
        return "Laya (fine-tuned on travel)"
    if backend != "ollama":
        return backend.capitalize()
    return f"Qwen stand-in ({name})" if name.startswith("qwen") else f"{name} stand-in"


def check_system1(model: str | None = None) -> None:
    """Exit with a one-line fix if the classifier can't run (offers to start Kev)."""
    if _backend(model)[0] == "kev" and ensure_kev():
        return
    problem = unavailable(model)
    if problem:
        print(problem)
        sys.exit(1)


def ensure_kev() -> bool:
    """Kev runs as a local server. If it's down, offer to start it in the background (it stays up)."""
    if _kev_up():
        return True
    print(f"Kev isn't running on {config.KEV_URL}.")
    if not sys.stdin.isatty():
        print("Start it with: ./kev.sh start")
        return False
    try:
        answer = input("Start it now in the background? It keeps running for the next labs. [Y/n] ")
    except (EOFError, KeyboardInterrupt):  # no answer: don't start anything
        answer = "n"
    if answer.strip().lower() not in ("", "y", "yes"):
        print("\nStart it later with: ./kev.sh start")
        return False
    return subprocess.run(["bash", str(KEV_SCRIPT), "start"]).returncode == 0


# --- plumbing ---------------------------------------------------------------

def _backend(model: str | None) -> tuple[str, str | None]:
    model = model or config.SYSTEM1_MODEL
    if model in ("jev", "kev", "laya", "laya-travel"):
        return model, None
    if model.startswith("ollama/"):
        return "ollama", model.removeprefix("ollama/")
    if "/" not in model and ":" in model:  # a bare Ollama tag like qwen3.5:4b
        return "ollama", model
    raise ValueError(f"SYSTEM1_MODEL {model!r} must be ollama/<name>, jev, kev, laya or laya-travel")


def _typed_answers(backend: str, state: str, questions: dict) -> dict:
    """Jev, Kev and Laya all take typed questions and answer them in one pass."""
    if backend == "laya-travel":
        with _LAYA_LOCK:  # the same GPU rule as plain Laya: one caller at a time
            return _laya_travel().predict(state, questions)["answers"]
    if backend == "laya":
        with _LAYA_LOCK:  # Laya runs on the GPU in this process: two callers at once crash Metal on a Mac
            return _laya_router().predict(state, questions)["answers"]
    if backend == "jev":
        payload = {"state": state, "model": "jev-latest", "questions": questions}
        headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}"}
        return _system_one_post(JEV_URL, payload, headers)["answers"]
    payload = {"state": state, "model": "kev-latest", "questions": questions}
    return _system_one_post(f"{config.KEV_URL}/v1/systemone", payload, None)["answers"]


def _system_one_post(url: str, payload: dict, headers: dict | None) -> dict:
    response = httpx.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()


def _kev_up() -> bool:
    try:
        httpx.get(config.KEV_URL, timeout=5)
        return True
    except httpx.HTTPError:
        return False


def laya_installed() -> bool:
    """Is the laya package installed? (Cheap: doesn't load a model.)"""
    return importlib.util.find_spec("laya") is not None


def quiet_laya() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")  # quiet the model download check
    # Laya warns that its confidence values are uncalibrated; we only use its probabilities.
    warnings.filterwarnings("ignore", message="laya: this checkpoint")


@functools.cache
def _laya_router():
    quiet_laya()
    try:
        from laya import Router
    except ImportError:
        return None
    return Router()


@functools.cache
def _laya_travel():
    """Lab 10b's fine-tuned Laya, loaded once."""
    quiet_laya()
    import laya

    return laya.Agent(str(config.LAYA_TRAVEL_DIR))


def _post(payload: dict) -> dict:
    response = httpx.post(f"{config.OLLAMA_HOST}/api/chat", json=payload, timeout=120)
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


def _ollama_ask(name: str, state: str, question: str, labels: list[str]) -> dict[str, float]:
    payload = {
        "model": name,
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
