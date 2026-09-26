# Lab 11: chat history. Each chat is a harness session; this keeps its title and settings.
from __future__ import annotations  # ChatStore has a list() method; keep annotations lazy
import json
import re
import shutil
import time
import uuid
from pathlib import Path

from common import config


def title_for(message: str, limit: int = 40) -> str:
    text = " ".join(message.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def turns_from_messages(messages: list[dict]) -> list[dict]:
    """The user's and assistant's words: no tool calls or results, no feedback the gate/check injected."""
    turns: list[dict] = []
    for message in messages:
        text = "\n".join(block["text"] for block in message.get("content", []) if "text" in block).strip()
        text = re.sub(r"\n*Attached file: .*", "", text).strip()  # a note for the agent, not for the reader
        text = text.split("</think>")[-1].strip()  # reasoning some models (Kimi) write as text
        if not text or text.startswith("[system1-"):  # e.g. "[system1-completion-check] Your answer skipped…"
            continue
        if turns and turns[-1]["role"] == message["role"]:  # one reply spread over several messages
            turns[-1]["text"] += "\n\n" + text
        else:
            turns.append({"role": message["role"], "text": text})
    return turns


def portable_tool_ids(messages: list[dict]) -> None:
    """Rewrite tool-call ids so any model accepts the history (Claude on Bedrock only allows [a-zA-Z0-9_-])."""
    for message in messages:
        for block in message.get("content", []):
            for kind in ("toolUse", "toolResult"):
                if kind in block and "toolUseId" in block[kind]:
                    block[kind]["toolUseId"] = re.sub(r"[^a-zA-Z0-9_-]", "_", block[kind]["toolUseId"])


class ChatStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "chats").mkdir(parents=True, exist_ok=True)

    def _path(self, chat_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{12}", chat_id):  # ids come from create(); anything else could escape data/
            raise ValueError(f"Not a chat id: {chat_id!r}")
        return self.root / "chats" / f"{chat_id}.json"

    def _read(self, chat_id: str) -> dict:
        return json.loads(self._path(chat_id).read_text())

    def _write(self, chat: dict) -> None:
        self._path(chat["id"]).write_text(json.dumps(chat, indent=2))

    def exists(self, chat_id: str) -> bool:
        return bool(re.fullmatch(r"[0-9a-f]{12}", chat_id)) and self._path(chat_id).exists()

    def create(self) -> str:
        chat_id = uuid.uuid4().hex[:12]
        now = time.time_ns()
        self._write({"id": chat_id, "title": "New chat", "created_at": now, "updated_at": now,
                     "model": config.MAIN_MODEL, "system1_model": config.SYSTEM1_MODEL, "connectors": [],
                     "files": [], "pending_files": []})
        return chat_id

    def list(self) -> list[dict]:
        chats = [json.loads(p.read_text()) for p in (self.root / "chats").glob("*.json")]
        chats.sort(key=lambda c: c["updated_at"], reverse=True)
        return [{"id": c["id"], "title": c["title"], "updated_at": c["updated_at"] // 1_000_000} for c in chats]

    def settings(self, chat_id: str) -> dict:
        chat = self._read(chat_id)
        return {key: chat[key] for key in ("model", "system1_model", "connectors")}

    def save_settings(self, chat_id: str, **changes) -> None:
        chat = self._read(chat_id)
        chat.update({k: v for k, v in changes.items() if v is not None})
        self._write(chat)

    def files(self, chat_id: str) -> list[dict]:
        return self._read(chat_id).get("files", [])

    def add_file(self, chat_id: str, info: dict) -> None:
        chat = self._read(chat_id)
        chat["files"] = [f for f in chat.get("files", []) if f["name"] != info["name"]] + [info]
        chat["pending_files"] = chat.get("pending_files", []) + [info["path"]]
        self._write(chat)

    def take_pending_files(self, chat_id: str) -> list[str]:
        """Files uploaded since the last message; the next message tells the agent about them."""
        chat = self._read(chat_id)
        pending, chat["pending_files"] = chat.get("pending_files", []), []
        self._write(chat)
        return pending

    def set_title(self, chat_id: str, title: str) -> None:
        self.save_settings(chat_id, title=title)

    def touch(self, chat_id: str) -> None:
        self.save_settings(chat_id, updated_at=time.time_ns())

    def title(self, chat_id: str) -> str:
        return self._read(chat_id)["title"]

    def delete(self, chat_id: str) -> None:
        self._path(chat_id).unlink(missing_ok=True)
        shutil.rmtree(self.root / "sessions" / "session" / chat_id, ignore_errors=True)
        shutil.rmtree(self.root / "files" / chat_id, ignore_errors=True)
