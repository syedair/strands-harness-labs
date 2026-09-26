# Lab 11: turn the gate's and check's decisions into events the web UI can show.
import re
from pathlib import Path
from types import SimpleNamespace

from strands import tool
from strands.interventions import Deny, Proceed

from lab7_tool_call_gate import ToolCallGate
from lab8_completion_check import CompletionCheck

# Which probability explains each gate decision (the reasons come from lab 7's ToolCallGate.block).
RULE_PROB = {
    "the tool doesn't match the request": "matches_intent",
    "ask the user instead of guessing": "args_grounded",
    "too early, clarify first": "premature",
}


def decision(source: str, action, probs: dict[str, float], why: str | None = None) -> dict:
    kind = "proceed" if isinstance(action, Proceed) else "deny" if isinstance(action, Deny) else "guide"
    if kind == "proceed" and not (source == "check" and why):
        why = None
    elif why is None:
        why = getattr(action, "reason", None)
    key = "answered_everything" if source == "check" else RULE_PROB.get(why, "args_grounded")
    return {"type": "decision", "source": source, "action": kind, "why": why,
            "p": round(probs[key], 2) if key in probs else None, "probs": {k: round(v, 2) for k, v in probs.items()}}


class WebGate(ToolCallGate):
    """Lab 7's gate, plus: record the tool call and the decision for the UI."""

    def __init__(self, events: list[dict]):
        super().__init__()
        self.events = events
        self.last_why = None
        self.remembered: list[str] = []  # notes memory recalled in this chat: facts the user told us, so they ground

    def context(self, event) -> str:
        """Lab 7 looks only at what the user typed; here, what we remember about them counts too."""
        known = "\n".join(f"- {note}" for note in self.remembered)
        return super().context(event) + (f"\n\nWhat we remember about the user:\n{known}" if known else "")

    def before_tool_call(self, event):
        self.events.append({"type": "tool", "name": event.tool_use["name"], "input": event.tool_use.get("input", {})})
        if event.tool_use["name"] != "web_fetch":
            return Proceed()  # only judge calls whose arguments should come from the user
        action = super().before_tool_call(event)
        self.events.append(decision("gate", action, self.last_probs, why=self.last_why))
        return action


class WebCheck(CompletionCheck):
    """Lab 8's completion check, plus: judge the CURRENT message and record the decision for the UI."""

    def __init__(self, events: list[dict]):
        super().__init__()
        self.events = events
        self.request = ""  # set at the start of every turn

    def after_model_call(self, event):
        self.last_probs = None
        if self.request and not has_several_parts(self.request):
            return Proceed()  # a one-question request can't be half answered: nothing for the check to catch
        if self.request:  # lab 8 reads messages[0]; in a chat that's the first turn, not this one
            current = {"role": "user", "content": [{"text": self.request}]}
            event = SimpleNamespace(stop_response=event.stop_response, agent=SimpleNamespace(messages=[current]))
        action = super().after_model_call(event)
        if self.last_probs is not None:
            gave_up = isinstance(action, Proceed) and self.last_probs["answered_everything"] < 0.6
            why = f"gave up after {self.MAX_GUIDES} retries" if gave_up else None  # not a pass: out of retries
            self.events.append(decision("check", action, self.last_probs, why=why))
        return action


def has_several_parts(request: str) -> bool:
    """'Weather and what to pack?' has two parts; 'what's my name' has one."""
    text = request.lower()
    return text.count("?") > 1 or any(joiner in text for joiner in (" and ", " also ", "; ", ". "))


class TurnHandlers:
    """The gate and the check for one chat. Reset at the start of every turn."""

    def __init__(self, events: list[dict]):
        self.events = events
        self.gate = WebGate(events)
        self.check = WebCheck(events)
        self.on_recall = None  # e.g. count hits per note
        self.recalled: set[frozenset] = set()  # recalls already reported this turn
        self.forgot = False  # this turn deleted memories: don't save the request to forget as a new one

    def recall(self, ids: list[str], texts: list[str], scores: list[float] | None = None, query: str | None = None) -> None:
        """Called by the memory store when a search returns notes: which ones, how relevant, for what."""
        if frozenset(ids) in self.recalled:  # every store is searched before every model call; report each once
            return
        self.recalled.add(frozenset(ids))
        self.gate.remembered = list(dict.fromkeys(self.gate.remembered + texts))[-30:]  # the most recent
        shown = re.split(r"\s*<system-reminder>", query or "")[0].strip()  # drop context the harness appends
        self.events.append({"type": "memory", "ids": ids, "scores": scores or [], "query": shown})
        if self.on_recall:
            self.on_recall(ids)

    def stored(self, note_id: str) -> None:
        """Called by the memory store when the harness saves a note."""
        self.events.append({"type": "stored", "ids": [note_id]})

    def start_turn(self, message: str) -> None:
        self.check.request = message
        self.recalled = set()
        self.gate.blocks = 0
        self.check.guides = 0
        self.forgot = False


def forget_tool(turn: TurnHandlers, notes: Path, judge=None):
    """A tool the agent calls when the user asks it to forget something (the harness only adds memories)."""
    import memory  # memory imports the harness; keep events importable on its own

    @tool
    def forget_memory(about: str = "", everything: bool = False) -> str:
        """Delete saved memories about something the user asked you to forget.

        Args:
            about: The topic in the user's own words, plus any names or values you remember for it,
                e.g. "Istanbul" or "my name (John, Syed)". Don't narrow it to one memory.
            everything: True only when the user clearly asks you to forget everything you know about them.
        """
        before = {p.name: p.read_text().strip() for p in Path(notes).glob("*.md")}
        if everything:
            for note_id in before:
                memory.forget(notes, note_id)
            ids, about = list(before), "everything"
        else:
            ids = memory.forget_about(notes, about, judge or memory.system1_forget)
        if not ids:
            return f"Found nothing saved about {about!r}; nothing was deleted."
        turn.forgot = True
        turn.events.append({"type": "forgot", "ids": ids})
        deleted = "\n".join(f"- {before[i]}" for i in ids)
        return f"Deleted {len(ids)} saved memories about {about!r}. They are gone now:\n{deleted}"

    return forget_memory
