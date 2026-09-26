# Lab 9: System 1 router — easy requests go to a cheap model, hard ones to a strong one.
import asyncio

from strands.models.routing import ModelRouter, RoutingCandidate
from strands_harness import create_harness

from common.chat import chat, wants_chat
from common.config import BIG_MODEL, SMALL_MODEL, build_model, check_ollama
from common.system1 import check_system1, yes_no

INSTRUCTIONS = (
    "You are a friendly travel assistant. Keep answers short and practical.\n"
    "For weather, fetch https://wttr.in/<city>?format=3 with web_fetch."
)


def latest_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message["role"] == "user":
            texts = [block["text"] for block in message["content"] if "text" in block]
            if texts:
                return "\n".join(texts)
    return ""


class System1Strategy:
    """Asks the classifier whether the request is quick, then picks a candidate by name."""

    async def select(self, context, **kwargs):
        if context.attempts:
            return None  # a call failed: let the router's default handle it
        request = latest_user_text(context.messages)
        p_quick = await asyncio.to_thread(  # System 1 observes...
            yes_no,
            f"User request: {request}",
            "Is this a quick factual question that can be answered in one or two sentences?",
        )
        pick = "small" if p_quick >= 0.5 else "big"  # ...plain Python decides.
        print(f"\n[router] P(quick question) = {p_quick:.2f} -> {pick}")
        return next(c for c in context.candidates if c.name == pick)


def main() -> None:
    check_ollama(SMALL_MODEL, BIG_MODEL)
    check_system1()
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

    agent("What's the weather in Paris?")
    agent("Plan a 5-day Istanbul itinerary under $1000, with a day trip and where to stay.")


if __name__ == "__main__":
    main()
