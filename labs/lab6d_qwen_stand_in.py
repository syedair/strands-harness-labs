# Lab 6d: no System 1 model? A small chat model on Ollama can stand in: ask for ONE token, read its probabilities.
import math
import sys

import httpx

from common.config import OLLAMA_HOST, check_ollama

MODEL = "qwen3.5:4b"
STATE = """user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")"""
QUESTION = "Did the user say which city they mean?"


def main() -> None:
    check_ollama(MODEL)
    response = httpx.post(f"{OLLAMA_HOST}/api/chat", timeout=120, json={
        "model": MODEL,
        "think": False,  # no reasoning: answer straight away
        "stream": False,
        "logprobs": True,  # NEW: return how likely each candidate token was
        "top_logprobs": 20,
        "options": {"num_predict": 1, "temperature": 0},  # generate exactly one token
        "messages": [
            {"role": "system", "content": "Answer with exactly one word: yes or no."},
            {"role": "user", "content": f"{STATE}\n\nQuestion: {QUESTION}"},
        ],
    }).json()

    # The model's top guesses for that one token, e.g. "no" 0.93, "yes" 0.05, "No" 0.01 ...
    yes = no = 0.0
    for rank, guess in enumerate(response["logprobs"][0]["top_logprobs"]):
        token, p = guess["token"].strip().lower(), math.exp(guess["logprob"])
        if rank < 5:
            print(f"  {guess['token']!r:10} {p:.3f}")
        yes += p if token == "yes" else 0
        no += p if token == "no" else 0

    if yes + no == 0:
        sys.exit("Neither yes nor no came up — rephrase the question.")
    p_city = yes / (yes + no)  # normalise across the two answers
    print(f"\n{QUESTION}\nP(yes) = {p_city:.2f}")
    print("Policy decision:", "ask the user for the city" if p_city < 0.5 else "go ahead")


if __name__ == "__main__":
    main()
