"""Draw a System 1 answer as bars in the terminal, so you can see every probability, not just the winner."""
import sys

WIDTH = 20


def bar(p: float, width: int = WIDTH, threshold: float | None = None) -> str:
    """A bar filled in proportion to p. `threshold` puts a │ at that point of the bar."""
    cells = ["█" if i < round(p * width) else "░" for i in range(width)]
    if threshold is not None:
        cells[round(threshold * width)] = "│"
    return "".join(cells)


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
        label = f"  {answer.type.capitalize():7} {questions[name].instructions}"
        print(label)
        if answer.type == "noul":
            color = "green" if answer.noul >= threshold else "red"
            print(f"          {'P(yes)':12}{_paint(bar(answer.noul, threshold=threshold), color)}  {answer.noul:.2f}")
        elif answer.type == "choice":
            order = list(getattr(questions[name], "criteria", None) or answer.probabilities)  # ties: as written
            for option, p in sorted(answer.probabilities.items(), key=lambda kv: (-kv[1], order.index(kv[0]))):
                color = "green" if option == answer.choice else "dim"
                print(f"          {option:12}{_paint(bar(p), color)}  {p:.2f}")
        elif answer.type == "score":
            for level, p in sorted(answer.probabilities.items()):
                print(f"          {answer.legend[level]:12}{_paint(bar(p), 'dim')}  {p:.2f}")
            print(f"          {'score':12}{answer.score:.2f}  (0 = {answer.legend[0]}, "
                  f"{max(answer.legend)} = {answer.legend[max(answer.legend)]})")
