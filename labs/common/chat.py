# Chat with any lab's agent in the terminal: uv run labs/<lab>.py --chat
import sys

from common import show


def wants_chat() -> bool:
    return "--chat" in sys.argv


def chat(agent, read=input, print_reply: bool = False) -> None:
    """Type a message, the agent streams its reply. 'exit' or Ctrl-D to quit.
    print_reply: for an agent that doesn't stream, print each reply once it's final."""
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
            reply = agent(message)  # the harness streams the reply to the terminal...
            if print_reply:  # ...unless streaming is off: then print the final reply
                print(f"assistant: {str(reply).strip()}")
            print()
