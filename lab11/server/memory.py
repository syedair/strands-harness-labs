# Lab 11: memory you can watch. The harness searches memory before every turn (and when the agent
# calls search_memory); this store reports which notes came back, so the UI can light them up.
import asyncio
import json
from datetime import datetime
import re
from pathlib import Path
from typing import Callable

import httpx
import numpy as np
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

    def __init__(self, *args, root: Path, on_search, on_store=None, relevance=None, embed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root, self.on_search, self.on_store, self.relevance = Path(root), on_search, on_store, relevance
        self.embed = embed or ollama_embed
        self.last_query: str | None = None

    async def search(self, query, options=None):
        if query.startswith("[system1-"):
            # the check's feedback became the latest "user" message; memories are injected for one
            # model call only, so the retry needs the ones for the user's real question again
            query = self.last_query or ""
        else:
            self.last_query = query
        if not query:
            return []
        limit = (options or {}).get("max_search_results") or 5
        if self.relevance is None:  # the harness's own keyword search
            entries = await super().search(query, options)
            scores = [float(e.metadata.get("score", 0)) for e in entries]
        else:
            files = sorted(self.root.glob("*.md"))
            notes = {f.name: f.read_text().strip() for f in files}
            saved = {f.name: f.stat().st_mtime for f in files}
            # retrieve the closest notes by meaning, then let System 1 rerank just those
            pool = await asyncio.to_thread(closest, _embeddings_file(self.root), notes, query, self.embed) if notes else []
            p = await asyncio.to_thread(self.relevance, query, {i: notes[i] for i in pool}) if pool else {}
            # most relevant first; on a tie the newer note wins
            ranked = sorted(((round(score, 2), saved[i], i) for i, score in p.items() if score >= 0.5), reverse=True)[:limit]
            entries = [
                MemoryEntry(
                    # the date lets the model see which of two conflicting memories is newer
                    content=f"(saved {datetime.fromtimestamp(when):%Y-%m-%d %H:%M}) {notes[i]}",
                    store_name=self.name, metadata={"path": i, "score": score},
                )
                for score, when, i in ranked
            ]
            scores = [score for score, _, _ in ranked]
        if entries:
            self.on_search([e.metadata["path"] for e in entries], [e.content for e in entries], scores, query)
        return entries

    async def add(self, content, metadata=None):
        key = await super().add(content, metadata)
        if self.on_store:
            self.on_store(key)
        return key


USER_FACTS_PROMPT = (
    "You extract durable facts about the user from what the user said.\n"
    "\n"
    'Return ONLY a JSON array of objects, each: {"content": string}. Each object is one discrete, self-contained '
    "fact the user stated about themselves: who they are, where they live, their plans, preferences and decisions. "
    "Write each fact in the third person about the user, never in the user's own words: "
    '"I am Syed" becomes "The user\'s name is Syed.", "we fly on Friday" becomes "The user flies on Friday." '
    "Do not include questions, chit-chat, guesses, or anything the user did not say. If there is nothing worth "
    "remembering, return []."
)


def user_said(messages: list[dict]) -> list[dict]:
    """The user's own words: no assistant replies, tool results, System 1 feedback or attachment notes."""
    said = []
    for message in messages:
        if message.get("role") != "user":
            continue
        text = "\n".join(block["text"] for block in message.get("content", []) if "text" in block)
        text = re.sub(r"\n*Attached file: .*", "", text).strip()
        if text and not text.startswith("[system1-"):
            said.append({"role": "user", "content": [{"text": text}]})
    return said


class UserOnlyExtractor(ModelExtractor):
    """Saves only what the user said. Otherwise the assistant's answers, which restate recalled memories and
    add guesses, come back as new "facts" every turn."""

    def __init__(self, model):
        super().__init__(model=model, system_prompt=USER_FACTS_PROMPT)

    async def extract(self, messages, context=None):
        said = user_said(messages)
        return await super().extract(said, context) if said else []


def store_for(model: str, root: Path, on_search, extract: bool = True, on_store=None, relevance=None, embed=None) -> WatchedStore:
    """Built like the harness's default store: markdown notes under `root`, facts extracted by a model."""
    kwargs = {"name": "memory", "storage": LocalFileStorage(str(root)).namespace(""), "writable": True}
    if extract:
        kwargs["extraction"] = ExtractionConfig(extractor=UserOnlyExtractor(resolve_web_fetch_model(model, None)))
    return WatchedStore(root=root, on_search=on_search, on_store=on_store, relevance=relevance, embed=embed, **kwargs)


FORGET_QUESTION = "Does this fact mention {about}, even in passing? Fact: {fact}"


def system1_forget(about: str, notes: dict[str, str]) -> dict[str, float]:
    """System 1 decides which memories the user means: one yes/no question per note."""
    from common.system1 import yes_no_many

    return yes_no_many(f"The user said: forget {about}.", {i: FORGET_QUESTION.format(about=about, fact=t) for i, t in notes.items()})


COMMON = {"the", "and", "about", "user", "users", "my", "our", "me", "that", "this", "with", "from", "discussion",
          "related", "memory", "memories", "everything", "anything", "all", "his", "her", "their"}


def topic_words(about: str) -> set[str]:
    """The words that make a note obviously about the topic ("Istanbul", "John"); not "the" or "user"."""
    return {w for w in re.findall(r"[a-z0-9]+", about.lower()) if len(w) >= 3 and w not in COMMON}


def forget_about(root: Path, about: str, judge=system1_forget, embed=None) -> list[str]:
    """Delete every note the judge says is about `about` (p >= 0.5). Returns the ids it deleted."""
    notes = {p.name: p.read_text() for p in Path(root).glob("*.md")}
    if not notes:
        return []
    words = topic_words(about)
    named = [i for i, text in notes.items() if words & set(re.findall(r"[a-z0-9]+", text.lower()))]  # says it outright
    rest = {i: t for i, t in notes.items() if i not in named}
    pool = closest(_embeddings_file(root), rest, about, embed or ollama_embed) if rest else []  # the likeliest of the rest, by meaning
    scores = judge(about, {i: rest[i] for i in pool}) if pool else {}  # System 1 for the ones that say it another way
    doomed = named + [i for i in pool if scores.get(i, 0.0) >= 0.5]
    for note_id in doomed:
        forget(root, note_id)
    return doomed


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
    together_file = _together_file(root)
    if together_file.exists():
        together = {k: v for k, v in json.loads(together_file.read_text()).items() if note_id not in k.split("|")}
        together_file.write_text(json.dumps(together))


def _hits_file(root: Path) -> Path:
    # next to the notes folder, not inside it: the memory search reads every file in there
    return Path(root).parent / f"{Path(root).name}_hits.json"


def _together_file(root: Path) -> Path:
    return Path(root).parent / f"{Path(root).name}_together.json"


def _pair(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def record_hits(root: Path, ids: list[str]) -> None:
    """Count each recall, and each pair recalled together: notes that fire together wire together."""
    path = _hits_file(root)
    hits = json.loads(path.read_text()) if path.exists() else {}
    for note_id in ids:
        hits[note_id] = hits.get(note_id, 0) + 1
    path.write_text(json.dumps(hits))
    together_path = _together_file(root)
    together = json.loads(together_path.read_text()) if together_path.exists() else {}
    unique = sorted(set(ids))
    for i, a in enumerate(unique):
        for b in unique[i + 1:]:
            together[_pair(a, b)] = together.get(_pair(a, b), 0) + 1
    together_path.write_text(json.dumps(together))


def ollama_embed(texts: list[str]) -> list[list[float]] | None:
    """Embeddings from Ollama's nomic-embed-text, or None if it isn't available."""
    try:
        response = httpx.post(f"{OLLAMA_HOST}/api/embed", json={"model": "nomic-embed-text", "input": texts}, timeout=30)
        response.raise_for_status()
        return response.json()["embeddings"]
    except httpx.HTTPError:
        return None


CANDIDATES = 12  # notes System 1 reranks; measured: the right notes were in the embedding top 12 86% of the time


def _embeddings_file(root: Path) -> Path:
    return Path(root).parent / f"{Path(root).name}_embeddings.json"  # beside the notes, like the hit counts


def note_vectors(cache: Path, notes: dict[str, str], embed=ollama_embed) -> dict[str, list[float]] | None:
    """Each note's embedding, cached in `cache` and recomputed only when a note changes. None without a model."""
    path = Path(cache)
    cache = json.loads(path.read_text()) if path.exists() else {}
    fresh = {i: c for i, c in cache.items() if i in notes}  # forgotten notes drop out
    stale = [i for i in notes if fresh.get(i, {}).get("text") != notes[i]]  # new or edited notes
    if stale:
        vectors = embed([notes[i] for i in stale])
        if vectors is None:
            return None
        fresh.update({i: {"text": notes[i], "vector": v} for i, v in zip(stale, vectors)})
    if stale or len(fresh) != len(cache):
        path.write_text(json.dumps(fresh))
    return {i: fresh[i]["vector"] for i in notes}


def closest(cache: Path, notes: dict[str, str], query: str, embed=ollama_embed, k: int = CANDIDATES) -> list[str]:
    """The k notes nearest the query by meaning (embeddings cached in `cache`). All of them when there are few,
    or no embedding model."""
    if len(notes) <= k:
        return list(notes)
    vectors = note_vectors(cache, notes, embed)
    asked = embed([query]) if vectors is not None else None
    if asked is None:
        return list(notes)
    ids = list(notes)
    matrix = _unit(np.array([vectors[i] for i in ids]))
    scores = matrix @ _unit(np.array(asked[0]))
    return [ids[j] for j in np.argsort(-scores)[:k]]


def _unit(a):
    """Rows (or a vector) scaled to length 1, so a dot product is the cosine."""
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


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
    vectors = note_vectors(_embeddings_file(root), notes, embed) if embed else None
    pairs = []
    if vectors:  # every pair at once: the cosine of each note with each other
        matrix = _unit(np.array([vectors[i] for i in ids]))
        similar = np.triu(matrix @ matrix.T, k=1)
        for a, b in zip(*np.nonzero(similar > threshold)):
            pairs.append((float(similar[a, b]), ids[a], ids[b]))
    else:
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                if _names(notes[ids[a]]) & _names(notes[ids[b]]):
                    pairs.append((1.0, ids[a], ids[b]))
    pairs.sort(reverse=True)
    degree: dict[str, int] = {}
    links: dict[str, dict] = {}
    for weight, a, b in pairs:  # links by meaning: each note's strongest few
        if degree.get(a, 0) < per_node and degree.get(b, 0) < per_node:
            links[_pair(a, b)] = {"source": min(a, b), "target": max(a, b), "weight": round(weight, 2), "together": 0}
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
    together_file = _together_file(root)
    together = json.loads(together_file.read_text()) if together_file.exists() else {}
    for key, count in together.items():  # links by use: notes recalled together
        a, b = key.split("|")
        if a in notes and b in notes:
            links.setdefault(key, {"source": a, "target": b, "weight": 0.0, "together": 0})["together"] = count
    nodes = [{"id": i, "text": notes[i][:300], "hits": hits.get(i, 0), "created": created[i]} for i in ids]
    return {"nodes": nodes, "links": list(links.values())}
