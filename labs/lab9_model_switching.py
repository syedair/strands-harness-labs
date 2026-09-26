# Lab 9: System 1 router — easy requests go to a cheap model, hard ones to a strong one.
import asyncio

from strands.models.routing import ModelRouter, RoutingCandidate
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import BIG_MODEL, SMALL_MODEL, build_model, check_ollama
from common.show import bar, wait
from common.system1 import check_system1, display_name, yes_no

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def latest_user_text(messages: list[dict]) -> str:
    """The user's latest message (tool results are "user" messages too, but have no text)."""
    for message in reversed(messages):
        if message["role"] == "user":
            texts = [block["text"] for block in message["content"] if "text" in block]
            if texts:
                return "\n".join(texts)
    return ""


class System1Strategy:
    """A custom routing strategy: the ModelRouter calls select() once per message you send (and again if a
    model call fails), and we return which candidate answers. That model then handles the whole reply,
    tool calls included. Here System 1 judges the request, and a threshold picks small or big."""

    QUICK = 0.5  # the policy knob: at or above this, the small model answers
    PAUSE = True  # wait for Enter before asking System 1 (only in a terminal)

    async def select(self, context, **kwargs):
        if context.attempts:
            return None  # a model call failed: decline, and the router surfaces the error
        # 1. What the user asked.
        request = latest_user_text(context.messages)
        print("\n  router · which model should answer this?")
        if self.PAUSE:
            wait(f"press Enter to ask {display_name()}")
        # 2. Ask System 1 one question. It only gives a probability: it never decides.
        p_quick = await asyncio.to_thread(  # System 1 observes...
            yes_no,
            f"User request: {request}",
            "Is this a quick factual question that can be answered in one or two sentences?",
        )
        # 3. ...plain Python decides: quick questions go to the small, cheap model; the rest to the big one.
        pick = "small" if p_quick >= self.QUICK else "big"
        print(f"    quick question?  {bar(p_quick, threshold=self.QUICK)}  {p_quick:.2f}")
        print(f"  router → {pick}: {SMALL_MODEL if pick == 'small' else BIG_MODEL}")
        return next(c for c in context.candidates if c.name == pick)  # the router calls this model


def main() -> None:
    check_ollama(SMALL_MODEL, BIG_MODEL)
    check_system1()
    print(f"System 1: {display_name()}")  # set SYSTEM1_MODEL in .env to switch
    router = ModelRouter(
        [
            RoutingCandidate(model=build_model(SMALL_MODEL), name="small"),  # e.g. Kimi K2.5
            RoutingCandidate(model=build_model(BIG_MODEL), name="big"),  # e.g. Kimi K3
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

    if wants_chat():  # uv run labs/<this lab>.py --chat
        chat(agent)
        return

    for question in ["What's the weather in Paris?",
                     "Plan a 5-day Istanbul itinerary under $1000, with a day trip and where to stay."]:
        print(f"\nyou: {question}")
        agent(question)


if __name__ == "__main__":
    main()
