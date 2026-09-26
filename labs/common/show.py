"""Draw a System 1 answer as bars in the terminal, so you can see every probability, not just the winner."""
import sys

WIDTH = 20


def bar(p: float, width: int = WIDTH, threshold: float | None = None) -> str:
    """A bar filled in proportion to p. `threshold` puts a │ at that point of the bar."""
    cells = ["█" if i < round(p * width) else "░" for i in range(width)]
    if threshold is not None:
        cells[round(threshold * width)] = "│"
    return "".join(cells)


def _get(obj, key, default=None):
    """Answers and questions come as SDK objects (Jev, Kev) or plain dicts (Laya, our own helpers)."""
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _paint(text: str, color: str) -> str:
    codes = {"green": "32", "red": "31", "dim": "2", "bold": "1"}
    return f"\x1b[{codes[color]}m{text}\x1b[0m" if sys.stdout.isatty() else text


def _conversation_line(conversation: str) -> str:
    said, _, rest = conversation.partition("\n")
    return _paint(said.removeprefix("user: "), "bold") + (_paint(f"   ({rest})", "dim") if rest else "")


def pause(conversation: str) -> None:
    """Show the conversation, then wait for Enter before asking, so you can explain it first.
    Only waits in a real terminal: piped or tested runs go straight through."""
    print(_conversation_line(conversation))
    if sys.stdin.isatty():
        input(_paint("  press Enter to ask ", "dim"))


def show(conversation: str, questions: dict, answers: dict, threshold: float = 0.5, header: bool = True) -> None:
    """One card per conversation: the question, then a bar per probability.
    Noul: P(yes) against your threshold. Choice: P per option, best first. Score: P per level, then the score.
    header=False skips the conversation line (pause() already printed it)."""
    if header:
        print(_conversation_line(conversation))
    for name, answer in answers.items():
        kind = _get(answer, "type")
        print(f"  {kind.capitalize():7} {_get(questions[name], 'instructions')}")
        if kind == "noul":
            p = _get(answer, "noul")
            color = "green" if p >= threshold else "red"
            print(f"          {'P(yes)':14}{_paint(bar(p, threshold=threshold), color)}  {p:.2f}")
        elif kind == "choice":
            probs, best = _get(answer, "probabilities"), _get(answer, "choice")
            order = list(_get(questions[name], "criteria") or probs)  # ties: in the order you wrote them
            for option, p in sorted(probs.items(), key=lambda kv: (-kv[1], order.index(kv[0]))):
                print(f"          {option:14}{_paint(bar(p), 'green' if option == best else 'dim')}  {p:.2f}")
        elif kind == "score":
            legend = {int(k): v for k, v in _get(answer, "legend").items()}
            for level, p in sorted((int(k), v) for k, v in _get(answer, "probabilities").items()):
                print(f"          {legend[level]:14}{_paint(bar(p), 'dim')}  {p:.2f}")
            top = max(legend)
            print(f"          {'score':14}{_get(answer, 'score'):.2f}  (0 = {legend[0]}, {top} = {legend[top]})")
