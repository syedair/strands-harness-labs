# Lab 11: memory you can watch. The harness searches memory before every turn (and when the agent
# calls search_memory); this store reports which notes came back, so the UI can light them up.
import json
import math
import re
from pathlib import Path
from typing import Callable

import httpx
from strands.memory import ExtractionConfig, ModelExtractor
from strands.storage import LocalFileStorage
from strands.vended_memory_stores.file_memory_store import FileMemoryStore
from strands_harness.models import resolve_web_fetch_model

from common.config import OLLAMA_HOST


class WatchedStore(FileMemoryStore):
    """The harness's file memory store, plus a callback with what each search returned (ids and texts)."""

    def __init__(self, *args, on_search: Callable[[list[str], list[str]], None], **kwargs):
        super().__init__(*args, **kwargs)
        self.on_search = on_search

    async def search(self, query, options=None):
        entries = await super().search(query, options)
        found = [(e.metadata["path"], e.content) for e in entries if e.metadata and "path" in e.metadata]
        if found:
            self.on_search([i for i, _ in found], [t for _, t in found])
        return entries


def store_for(model: str, root: Path, on_search, extract: bool = True) -> WatchedStore:
    """Built like the harness's default store: markdown notes under `root`, facts extracted by a model."""
    kwargs = {"name": "memory", "storage": LocalFileStorage(str(root)).namespace(""), "writable": True}
    if extract:
        kwargs["extraction"] = ExtractionConfig(extractor=ModelExtractor(model=resolve_web_fetch_model(model, None)))
    return WatchedStore(on_search=on_search, **kwargs)


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
    notes = {p.name: p.read_text().strip() for p in sorted(root.glob("*.md"))} if root.exists() else {}
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
    nodes = [{"id": i, "text": notes[i][:300], "hits": hits.get(i, 0)} for i in ids]
    return {"nodes": nodes, "links": links}
