# Lab 6d: no System 1 model? A small chat model on Ollama can stand in: ask for ONE token, read its probabilities.
import math

import httpx
from common.config import OLLAMA_HOST, check_ollama
from common.show import bar, pause, show
from lab6a_jev import conversation, more  # the same conversations as lab 6a

MODEL = "qwen3.5:4b"

# One yes/no question. A chat model has no Choice or Score: we build a probability from one token.
questions = {"named_city": {"type": "noul", "instructions": "Did the user say which city they mean?"}}


def ask_one_token(state: str, question: str) -> list[tuple[str, float]]:
    """The model's top guesses for its one-token answer, e.g. [("no", 0.92), ("No", 0.07), ("yes", 0.01), ...]."""
    response = httpx.post(f"{OLLAMA_HOST}/api/chat", timeout=120, json={
        "model": MODEL,
        "think": False,  # no reasoning: answer straight away
        "stream": False,
        "logprobs": True,  # NEW: return how likely each candidate token was
        "top_logprobs": 20,
        "options": {"num_predict": 1, "temperature": 0},  # generate exactly one token
        "messages": [
            {"role": "system", "content": "Answer with exactly one word: yes or no."},
            {"role": "user", "content": f"{state}\n\nQuestion: {question}"},
        ],
    }).json()
    return [(g["token"], math.exp(g["logprob"])) for g in response["logprobs"][0]["top_logprobs"]]


def p_yes(guesses: list[tuple[str, float]]) -> float:
    """Add up every spelling of "yes" and of "no", then compare the two."""
    yes = sum(p for token, p in guesses if token.strip().lower() == "yes")
    no = sum(p for token, p in guesses if token.strip().lower() == "no")
    return yes / (yes + no) if yes + no else 0.5  # neither came up: we learned nothing


def main() -> None:
    check_ollama(MODEL)

    for state in [conversation, *more]:
        pause(state)  # show the conversation, then wait for Enter

        # Ask. One token, and how likely each candidate was.
        guesses = ask_one_token(state, questions["named_city"]["instructions"])
        print("  Qwen's top guesses for that one token:")
        for token, p in guesses[:4]:
            print(f"          {token!r:14}{bar(p)}  {p:.2f}")
        answers = {"named_city": {"type": "noul", "noul": p_yes(guesses)}}
        show(state, questions, answers, header=False)

        # Qwen only observes. Plain Python decides.
        if answers["named_city"]["noul"] < 0.5:
            print("  → ask which city\n")
        else:
            print("  → go\n")


if __name__ == "__main__":
    main()
