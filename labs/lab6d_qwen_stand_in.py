# Lab 6d: no System 1 model? A small chat model on Ollama can stand in: ask for ONE token, read its probabilities.
import math

import httpx

from common.config import OLLAMA_HOST, check_ollama
from common.travel_cases import CASES, short

MODEL = "qwen3.5:4b"
QUESTION = "Did the user say which city they mean?"


def p_yes(state: str, show_guesses: bool = False) -> float:
    response = httpx.post(f"{OLLAMA_HOST}/api/chat", timeout=120, json={
        "model": MODEL,
        "think": False,  # no reasoning: answer straight away
        "stream": False,
        "logprobs": True,  # NEW: return how likely each candidate token was
        "top_logprobs": 20,
        "options": {"num_predict": 1, "temperature": 0},  # generate exactly one token
        "messages": [
            {"role": "system", "content": "Answer with exactly one word: yes or no."},
            {"role": "user", "content": f"{state}\n\nQuestion: {QUESTION}"},
        ],
    }).json()

    # The model's top guesses for that one token, e.g. "no" 0.92, "No" 0.07, "yes" 0.01 ...
    yes = no = 0.0
    for rank, guess in enumerate(response["logprobs"][0]["top_logprobs"]):
        token, p = guess["token"].strip().lower(), math.exp(guess["logprob"])
        if show_guesses and rank < 5:
            print(f"    {guess['token']!r:10} {p:.3f}")
        yes += p if token == "yes" else 0
        no += p if token == "no" else 0
    return yes / (yes + no) if yes + no else 0.5  # neither came up: we learned nothing


def main() -> None:
    check_ollama(MODEL)
    print(f"Q: {QUESTION}\n\nTop guesses for the first case:")
    p_yes(CASES[0], show_guesses=True)

    print(f"\n{'user said':44}{'P(yes)':>8}  decision")
    for case in CASES:
        p_city = p_yes(case)
        print(f"{short(case):44}{p_city:8.2f}  {'ask which city' if p_city < 0.5 else 'go'}")


if __name__ == "__main__":
    main()
