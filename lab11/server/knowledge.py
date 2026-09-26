# Lab 11: a folder of your own markdown notes as a second, read-only memory store (KNOWLEDGE_DIR).
# Files at any depth are split into sections; recall is the same retrieve-then-rerank as memory.
import asyncio
import os
import re
from pathlib import Path

from strands.memory import MemoryEntry

import memory

MAX_CHARS = 1500  # a section longer than this is split at paragraphs, so embeddings and System 1 see all of it
NOTE_QUESTION = "Would this note help answer the user's message? Note: {note}"


def settings() -> tuple[Path, list[str] | None] | None:
    """KNOWLEDGE_DIR and the optional KNOWLEDGE_FOLDERS include list (comma-separated), or None when unset."""
    folder = os.environ.get("KNOWLEDGE_DIR")
    if not folder:
        return None
    folders = [f.strip() for f in os.environ.get("KNOWLEDGE_FOLDERS", "").split(",") if f.strip()] or None
    return Path(folder).expanduser(), folders


def system1_note_relevance(query: str, sections: dict[str, str]) -> dict[str, float]:
    """System 1 decides which notes matter: one yes/no question per section."""
    from common.system1 import yes_no_many

    return yes_no_many(f"User message: {query}", {i: NOTE_QUESTION.format(note=t) for i, t in sections.items()})


def load_sections(root: Path, folders: list[str] | None = None) -> dict[str, str]:
    """Every markdown file under root (hidden folders skipped, only `folders` if given), as sections
    keyed "path#n" and prefixed "path › heading" so each one says where it came from."""
    root = Path(root).expanduser()
    sections: dict[str, str] = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if folders and relative.parts[0] not in folders:
            continue
        for n, (heading, body) in enumerate(_split(path.read_text(errors="replace"), path.stem)):
            sections[f"{relative.as_posix()}#{n}"] = f"{relative.as_posix()} › {heading}\n{body}"
    return sections


def _split(text: str, title: str) -> list[tuple[str, str]]:
    """(heading, text) pieces: one per heading, long ones cut at paragraphs to at most MAX_CHARS."""
    pieces: list[tuple[str, str]] = []
    heading, lines = title, []

    def close():
        body = "\n".join(lines).strip()
        if body:
            pieces.extend((heading, chunk) for chunk in _chunks(body))

    for line in text.splitlines():
        match = re.match(r"#{1,6}\s+(.*)", line)
        if match:
            close()
            heading, lines = match.group(1).strip(), []
        else:
            lines.append(line)
    close()
    return pieces


def _chunks(body: str) -> list[str]:
    out, current = [], ""
    for paragraph in re.split(r"\n\s*\n", body):
        while len(paragraph) > MAX_CHARS:  # one enormous paragraph: cut it
            out.append(paragraph[:MAX_CHARS])
            paragraph = paragraph[MAX_CHARS:]
        if current and len(current) + len(paragraph) + 2 > MAX_CHARS:
            out.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        out.append(current)
    return out


class KnowledgeStore:
    """A read-only memory store over a notes folder. Nothing is ever written into the folder: its embedding
    cache lives in `cache`, and it accepts no new notes."""

    name = "knowledge"
    writable = False
    extraction = None
    max_search_results = 5

    def __init__(self, root: Path, cache: Path, on_search, folders: list[str] | None = None,
                 relevance=system1_note_relevance, embed=None):
        self.root, self.cache, self.folders = Path(root).expanduser(), Path(cache), folders
        self.on_search, self.relevance, self.embed = on_search, relevance, embed or memory.ollama_embed
        self.description = f"The user's own notes in {root} (read-only)"
        self.last_query: str | None = None

    async def search(self, query, options=None):
        if query.startswith("[system1-"):  # a retry after the completion check: search for the real question
            query = self.last_query or ""
        else:
            self.last_query = query
        if not query:
            return []
        limit = (options or {}).get("max_search_results") or self.max_search_results
        sections = await asyncio.to_thread(load_sections, self.root, self.folders)
        pool = await asyncio.to_thread(memory.closest, self.cache, sections, query, self.embed) if sections else []
        p = await asyncio.to_thread(self.relevance, query, {i: sections[i] for i in pool}) if pool else {}
        ranked = sorted(((round(s, 2), i) for i, s in p.items() if s >= 0.5), reverse=True)[:limit]
        entries = [MemoryEntry(content=sections[i], store_name=self.name, metadata={"path": f"kb:{i}", "score": s})
                   for s, i in ranked]
        if entries:
            self.on_search([e.metadata["path"] for e in entries], [e.content for e in entries],
                           [s for s, _ in ranked], query)
        return entries

    async def add(self, content, metadata=None):
        raise PermissionError(f"{self.root} is read-only: the app never writes into your notes folder")
