# System 1 stand-in: a small local chat model answers narrow, typed questions with probabilities
# (one token + its logprobs). Real System 1 models like Jev, Kev and Laya are compared in lab 10.
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
