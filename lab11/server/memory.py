# Lab 11: memory you can watch. The harness searches memory before every turn (and when the agent
# calls search_memory); this store reports which notes came back, so the UI can light them up.
import asyncio
import json
import math
import re
from pathlib import Path
from typing import Callable

import httpx
from strands.memory import ExtractionConfig, MemoryEntry, ModelExtractor
from strands.storage import LocalFileStorage
from strands.vended_memory_stores.file_memory_store import FileMemoryStore
from strands_harness.models import resolve_web_fetch_model

from common.config import OLLAMA_HOST


RECALL_QUESTION = "Would this fact about the user help answer their message? Fact: {fact}"


def system1_relevance(query: str, notes: dict[str, str]) -> dict[str, float]:
    """System 1 decides which memories matter: one yes/no question per note."""
    from common.system1 import yes_no_many

    return yes_no_many(f"User message: {query}", {i: RECALL_QUESTION.format(fact=t) for i, t in notes.items()})


class WatchedStore(FileMemoryStore):
    """The harness's file memory store, plus:
    - recall filtered by relevance (the harness's keyword search matches words like "the"), and
    - callbacks with what each search returned and each note saved, so the UI can show it."""

    def __init__(self, *args, root: Path, on_search, on_store=None, relevance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root, self.on_search, self.on_store, self.relevance = Path(root), on_search, on_store, relevance

    async def search(self, query, options=None):
        limit = (options or {}).get("max_search_results") or 5
        if self.relevance is None:  # the harness's own keyword search
            entries = await super().search(query, options)
            scores = [float(e.metadata.get("score", 0)) for e in entries]
        else:
            notes = {p.name: p.read_text().strip() for p in sorted(self.root.glob("*.md"))}
            p = await asyncio.to_thread(self.relevance, query, notes) if notes else {}
            ranked = sorted(((score, i) for i, score in p.items() if score >= 0.5), reverse=True)[:limit]
            entries = [MemoryEntry(content=notes[i], store_name=self.name, metadata={"path": i, "score": round(s, 2)})
                       for s, i in ranked]
            scores = [round(s, 2) for s, _ in ranked]
        if entries:
            self.on_search([e.metadata["path"] for e in entries], [e.content for e in entries], scores, query)
        return entries

    async def add(self, content, metadata=None):
        key = await super().add(content, metadata)
        if self.on_store:
            self.on_store(key)
        return key


def store_for(model: str, root: Path, on_search, extract: bool = True, on_store=None, relevance=None) -> WatchedStore:
    """Built like the harness's default store: markdown notes under `root`, facts extracted by a model."""
    kwargs = {"name": "memory", "storage": LocalFileStorage(str(root)).namespace(""), "writable": True}
    if extract:
        kwargs["extraction"] = ExtractionConfig(extractor=ModelExtractor(model=resolve_web_fetch_model(model, None)))
    return WatchedStore(root=root, on_search=on_search, on_store=on_store, relevance=relevance, **kwargs)


def forget(root: Path, note_id: str) -> None:
    """Delete one memory. The harness has no forget tool, but its notes are plain files."""
    path = Path(root) / note_id
    if Path(note_id).name != note_id or not note_id.endswith(".md") or not path.exists():
        raise ValueError(f"No memory called {note_id!r}")
    path.unlink()
    hits_file = _hits_file(root)
    if hits_file.exists():
        hits = json.loads(hits_file.read_text())
        hits.pop(note_id, None)
        hits_file.write_text(json.dumps(hits))


def _hits_file(root: Path) -> Path:
    # next to the notes folder, not inside it: the memory search reads every file in there
    return Path(root).parent / f"{Path(root).name}_hits.json"


def record_hits(root: Path, ids: list[str]) -> None:
    path = _hits_file(root)
    hits = json.loads(path.read_text()) if path.exists() else {}
    for note_id in ids:
        hits[note_id] = hits.get(note_id, 0) + 1
    path.write_text(json.dumps(hits))


def ollama_embed(texts: list[str]) -> list[list[float]] | None:
    """Embeddings from Ollama's nomic-embed-text, or None if it isn't available."""
    try:
        response = httpx.post(f"{OLLAMA_HOST}/api/embed", json={"model": "nomic-embed-text", "input": texts}, timeout=30)
        response.raise_for_status()
        return response.json()["embeddings"]
    except httpx.HTTPError:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _names(text: str) -> set[str]:
    """Capitalised words that aren't just starting a sentence: places, people, months."""
    words = set()
    for sentence in re.split(r"[.!?\n]+", text):
        tokens = re.findall(r"[A-Za-z][\w'-]*", sentence)
        words |= {t for t in tokens[1:] if t[0].isupper()}
    return words


def graph(root: Path, embed=ollama_embed, threshold: float = 0.6, per_node: int = 3) -> dict:
    """Nodes = notes; links = notes that mean similar things (or share a name, without embeddings)."""
    root = Path(root)
    files = sorted(root.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True) if root.exists() else []
    notes = {p.name: p.read_text().strip() for p in files}  # newest first
    created = {p.name: int(p.stat().st_mtime * 1000) for p in files}
    if not notes:
        return {"nodes": [], "links": []}
    hits_file = _hits_file(root)
    hits = json.loads(hits_file.read_text()) if hits_file.exists() else {}
    ids = list(notes)
    vectors = embed([notes[i] for i in ids]) if embed else None
    pairs = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if vectors:
                weight = _cosine(vectors[a], vectors[b])
            else:
                weight = 1.0 if _names(notes[ids[a]]) & _names(notes[ids[b]]) else 0.0
            if weight > threshold:
                pairs.append((weight, ids[a], ids[b]))
    pairs.sort(reverse=True)
    degree: dict[str, int] = {}
    links = []
    for weight, a, b in pairs:  # keep each note's strongest few links
        if degree.get(a, 0) < per_node and degree.get(b, 0) < per_node:
            links.append({"source": a, "target": b, "weight": round(weight, 2)})
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
    nodes = [{"id": i, "text": notes[i][:300], "hits": hits.get(i, 0), "created": created[i]} for i in ids]
    return {"nodes": nodes, "links": links}
