# Lab 11: folders of your own markdown notes (an Obsidian vault works) as read-only memory stores, added in Settings.
# Files at any depth are split into sections; recall is the same retrieve-then-rerank as memory.
from __future__ import annotations  # Bases has a list() method; keep annotations lazy
import asyncio
import hashlib
import json
import re
import time
from pathlib import Path

from strands.memory import MemoryEntry

import memory

MAX_CHARS = 1500  # a section longer than this is split at paragraphs, so embeddings and System 1 see all of it
NOTE_QUESTION = "Would this note help answer the user's message? Note: {note}"


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

    writable = False
    extraction = None
    max_search_results = 5

    def __init__(self, root: Path, cache: Path, on_search, folders: list[str] | None = None,
                 relevance=system1_note_relevance, embed=None, key: str = "knowledge"):
        self.root, self.cache, self.folders = Path(root).expanduser(), Path(cache), folders
        self.name = key if key == "knowledge" else f"knowledge-{key}"
        self.prefix = "kb:" if key == "knowledge" else f"kb:{key}/"
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
        entries = [MemoryEntry(content=sections[i], store_name=self.name, metadata={"path": f"{self.prefix}{i}", "score": s})
                   for s, i in ranked]
        if entries:
            self.on_search([e.metadata["path"] for e in entries], [e.content for e in entries],
                           [s for s, _ in ranked], query)
        return entries

    async def add(self, content, metadata=None):
        raise PermissionError(f"{self.root} is read-only: the app never writes into your notes folder")


MAX_FILES = 5000  # refuse bigger folders, so pointing at your home folder by mistake can't index everything


class Bases:
    """The knowledge bases chosen in Settings, saved in data/knowledge.json."""

    def __init__(self, data: Path, embed=None):
        self.data, self.embed = Path(data), embed
        self.file = self.data / "knowledge.json"

    def _read(self) -> dict:
        if self.file.exists():
            return json.loads(self.file.read_text())
        state = {"bases": []}  # a fresh clone starts with none; add folders in Settings
        self._write(state)
        return state

    def _write(self, state: dict) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(state, indent=2))

    def list(self) -> list[dict]:
        return self._read()["bases"]

    def cache(self, base_id: str) -> Path:
        return self.data / "knowledge" / f"{base_id}.json"

    def add(self, path: str, folders: list[str] | None = None, embed=None) -> dict:
        state = self._read()
        base = self._index(self._new(path, folders), embed)
        state["bases"] = [b for b in state["bases"] if b["path"] != base["path"]] + [base]
        self._write(state)
        return base

    def index(self, base_id: str, embed=None) -> dict:
        state = self._read()
        (base,) = [b for b in state["bases"] if b["id"] == base_id] or [None]
        if base is None:
            raise KeyError(base_id)
        base.update(self._index(base, embed))
        self._write(state)
        return base

    def remove(self, base_id: str) -> None:
        state = self._read()
        state["bases"] = [b for b in state["bases"] if b["id"] != base_id]
        self.cache(base_id).unlink(missing_ok=True)
        self._write(state)

    def stores(self, on_search) -> list[KnowledgeStore]:
        return [KnowledgeStore(Path(b["path"]).expanduser(), cache=self.cache(b["id"]), on_search=on_search,
                               folders=b.get("folders"), key=b["id"]) for b in self.list()]

    def sections(self) -> dict[str, str]:
        """Every base's sections, keyed like their stores report them ("kb:<base>/<file>#<n>")."""
        out = {}
        for b in self.list():
            for i, text in load_sections(Path(b["path"]).expanduser(), b.get("folders")).items():
                out[f"kb:{b['id']}/{i}"] = text
        return out

    def _new(self, path: str, folders: list[str] | None) -> dict:
        root = Path(path).expanduser()
        if not root.exists():
            raise ValueError(f"{path} doesn't exist")
        if not root.is_dir():
            raise ValueError(f"{path} isn't a folder")
        files = [f for f in root.rglob("*.md") if not any(part.startswith(".") for part in f.relative_to(root).parts)]
        if len(files) > MAX_FILES:
            raise ValueError(f"{path} has more than {MAX_FILES} markdown files; pick a smaller folder")
        if not files:
            raise ValueError(f"{path} has no markdown files")
        slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "notes"
        digest = hashlib.sha1(str(root.resolve()).encode()).hexdigest()[:6]
        return {"id": f"{slug}-{digest}", "path": path, "folders": folders or None}

    def _index(self, base: dict, embed=None) -> dict:
        """Split the folder into sections and embed them now, so the first recall doesn't wait."""
        sections = load_sections(Path(base["path"]).expanduser(), base.get("folders"))
        self.cache(base["id"]).parent.mkdir(parents=True, exist_ok=True)
        vectors = memory.note_vectors(self.cache(base["id"]), sections, embed or self.embed or memory.ollama_embed)
        return {**base, "files": len({i.split("#")[0] for i in sections}), "sections": len(sections),
                "embedded": vectors is not None, "indexed_at": int(time.time() * 1000)}
