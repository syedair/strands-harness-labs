# Chat with any lab's agent in the terminal: uv run labs/<lab>.py --chat
import sys

from common import show


def wants_chat() -> bool:
    return "--chat" in sys.argv


def chat(agent, read=input) -> None:
    """Type a message, the agent streams its reply. 'exit' or Ctrl-D to quit."""
    show.PAUSES = False  # the demo pauses would read your next message as "Enter"
    print("Chatting with the travel assistant. Type 'exit' to quit.\n")
    while True:
        try:
            message = read("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if message.lower() in ("exit", "quit"):
            return
        if message:
            agent(message)  # the harness streams the reply to the terminal
            print()
