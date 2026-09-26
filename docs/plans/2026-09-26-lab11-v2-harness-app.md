# Lab 11 v2 — The Harness App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn lab 11 into a full harness app — chat history, LLM and System 1 pickers, file upload, MCP connectors, an "Inside the harness" panel and a 3D memory globe that fires on recall — in its own `lab11/` folder.

**Architecture:** `lab11/server/` is a FastAPI app split by responsibility: `chats.py` (sessions on disk, turn history), `agents.py` (build a harness per chat from its settings), `events.py` (gate/check/memory → UI events, per-turn reset), `memory.py` (WatchedStore + graph), `connectors.py` (MCP presets and persistence), `app.py` (routes, streaming). `lab11/web/` is the v1 React app grown into a three-column layout; the stream reducer gains `memory` and `title` events.

**Tech Stack:** Python: FastAPI 0.141, uvicorn 0.54, python-multipart, strands-harness 0.1.x. Web: Vite 8, React 19, TypeScript, Tailwind 4, lucide-react 1.48, react-markdown, react-force-graph-3d 1.29, Vitest.

**Spec:** `docs/specs/2026-09-26-lab11-web-ui-design.md` (v2)

## Global Constraints

- Folder: `lab11/server/*.py`, `lab11/web/`, runtime data in `lab11/data/` (git-ignored). `lab11/server/app.py` adds `labs/` to `sys.path` once, with a comment, to import labs 7–8 and `common`.
- Run: `uv run --extra web lab11/server/app.py` (API :8000) and `cd lab11/web && npm run dev` (:5173, proxy `/api`).
- pytest `pythonpath = ["labs", "lab11/server"]`; lab 11 test modules start with `pytest.importorskip("fastapi")`.
- Theme, icons, motion exactly as the spec's Decisions section. No emoji in UI code.
- Event types exactly: `text`, `tool`, `decision` (`source, action, why, p, probs`), `memory` (`ids`), `title` (`title`), `done`, `error`. Every stream ends with `done` or `error`.
- LLM choices (id → label): `bedrock/moonshotai.kimi-k2.5` Kimi K2.5, `bedrock/nvidia.nemotron-super-3-120b` Nemotron Super, `bedrock/us.anthropic.claude-sonnet-5` Claude Sonnet 5, `bedrock/us.moonshotai.kimi-k3` Kimi K3, `ollama/gpt-oss:20b` gpt-oss 20B (local). Default = `config.MAIN_MODEL`.
- Upload limit 5 MB; extensions `.txt .md .csv .json .pdf`.
- Labs 1–10 unchanged except: lab 8 prints its "asked the user a question" early return; lab 7 records `last_why`.
- Branch `lab11-web-ui`; the v1 files `labs/lab11_web_server.py`, `web/`, `tests/test_lab11_server.py` move into `lab11/`.

## Review Focus

1. **Second and later turns in one chat** → gate and check judge the current message, counters start fresh each turn. Test in Task 2.
2. **Reopen a chat after a server restart** → the full history renders, and the next message continues it. Test in Task 3.
3. **Switch LLM mid-chat** → the agent is rebuilt on the same session; history is kept. Test in Task 3.
4. **An MCP server fails to start** → the chat still works; the connector shows the error. Test in Task 5.
5. **A memory search returns nothing / no notes exist yet** → the globe shows an empty state, no crash; `memory` event is omitted. Tests in Tasks 6 and 8.

---

### Task 1: Move lab 11 into `lab11/` and split the server

**Files:** `git mv labs/lab11_web_server.py lab11/server/app.py`, `git mv web lab11/web`, `git mv tests/test_lab11_server.py tests/lab11/test_app.py`; create `lab11/server/events.py` (move `decision`, `RULE_PROB`, `WebGate`, `WebCheck` there), `lab11/server/agents.py` (move `make_agent`, `INSTRUCTIONS`); `.gitignore` add `lab11/data/`; `pyproject.toml` pytest pythonpath; README run commands; `tests/test_labs_compile.py` count back to 14.

- [ ] Step 1: move files; add at top of `app.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "labs"))  # labs 7-8 and common/
```
- [ ] Step 2: `tests/lab11/test_app.py` first line after imports of pytest: `pytest.importorskip("fastapi")`; imports become `import app as server` and `import events`.
- [ ] Step 3: Run `uv run pytest -q` (all pass) and `uv sync && uv run pytest -q` (lab 11 tests skipped, rest pass), then `uv sync --extra laya --extra web`.
- [ ] Step 4: Commit "Lab 11: own folder; server split into modules".

### Task 2: Per-turn correctness and stream termination (v1 review fixes)

**Interfaces — Produces:** `events.TurnHandlers(events: list[dict])` with `.gate: WebGate`, `.check: WebCheck`, `.start_turn(message: str)`; `WebCheck` judges `self.request`; `WebGate`/`lab7.ToolCallGate` expose `last_why`.

- [ ] Step 1: failing tests (`tests/lab11/test_events.py`):
```python
import pytest
pytest.importorskip("fastapi")
from types import SimpleNamespace
import lab7_tool_call_gate as lab7
import lab8_completion_check as lab8
import events


def final(answer, first_user="What's the weather?"):
    return SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message={"content": [{"text": answer}]}),
                           agent=SimpleNamespace(messages=[{"role": "user", "content": [{"text": first_user}]}]))


def test_check_judges_the_current_message(monkeypatch):
    seen = []
    monkeypatch.setattr(lab8, "yes_no", lambda state, q: seen.append(state) or 0.9)
    turn = events.TurnHandlers([])
    turn.start_turn("Pack for 4 days in Istanbul")
    turn.check.after_model_call(final("Here is your list."))
    assert "Pack for 4 days in Istanbul" in seen[0] and "What's the weather?" not in seen[0]


def test_counters_reset_each_turn(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.9, "missing_info": 0.1,
                                                          "args_grounded": 0.1, "premature": 0.1})
    turn = events.TurnHandlers([])
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {"url": "https://wttr.in/X"}},
                           agent=SimpleNamespace(messages=[]))
    for _ in range(4):
        turn.gate.before_tool_call(call)
    turn.start_turn("again")
    assert turn.gate.blocks == 0 and turn.check.guides == 0


def test_deny_keeps_its_rule(monkeypatch):
    monkeypatch.setattr(lab7, "yes_no_many", lambda s, q: {"matches_intent": 0.9, "missing_info": 0.1,
                                                          "args_grounded": 0.1, "premature": 0.1})
    log = []
    turn = events.TurnHandlers(log)
    call = SimpleNamespace(tool_use={"name": "web_fetch", "input": {}}, agent=SimpleNamespace(messages=[]))
    for _ in range(lab7.ToolCallGate.MAX_BLOCKS + 1):
        turn.gate.before_tool_call(call)
    last = [e for e in log if e["type"] == "decision"][-1]
    assert last["action"] == "deny" and last["why"] == "ask the user instead of guessing"
```
Plus in `tests/lab11/test_app.py`: stream that raises after recording a tool event yields that `tool` event before `error`; a stream where `make_agent` raises yields exactly one `error`.
- [ ] Step 2: run → fail. Step 3: implement: lab 7 `block()` sets `self.last_why = why`; `events.decision` uses `last_why` for deny; `WebCheck.after_model_call` swaps in the current request by passing a shallow event whose `agent.messages[0]` is `{"role": "user", "content": [{"text": self.request}]}`; `TurnHandlers.start_turn` sets `check.request`, zeroes `gate.blocks`, `check.guides`; `app.py` wraps agent creation and `unavailable` in the `try`, drains events before `error`, `finally: events.clear()`. Lab 8: print `[check] -> Proceed (asked the user a question)` in the `?` branch; README lab 8 gains one sentence.
- [ ] Step 4: `uv run pytest -q` green. Commit.

### Task 3: Chats on disk — list, create, open, delete, switch model

**Files:** `lab11/server/chats.py`, `lab11/server/agents.py`, routes in `app.py`, `tests/lab11/test_chats.py`.

**Interfaces — Produces:** `chats.ChatStore(root: Path)` with `.create() -> str`, `.list() -> list[dict]` (`id, title, updated_at`), `.settings(id) -> dict` (`model, system1_model, connectors`), `.save_settings(id, **changes)`, `.set_title(id, title)`, `.delete(id)`; `agents.build(chat_id, settings, events) -> Agent` using `session={"id": chat_id, "dir": str(root/"sessions")}`; `chats.turns_from_messages(messages) -> list[dict]` (`{"role": "user"|"assistant", "text": str}`, tool/results omitted).

- [ ] Step 1: failing tests:
```python
import pytest
pytest.importorskip("fastapi")
import chats


def test_create_list_title_delete(tmp_path):
    store = chats.ChatStore(tmp_path)
    a = store.create(); b = store.create()
    store.set_title(a, "Paris weather")
    listed = store.list()
    assert [c["id"] for c in listed] == [b, a] and listed[1]["title"] == "Paris weather"
    store.delete(a)
    assert [c["id"] for c in store.list()] == [b]


def test_settings_persist_across_instances(tmp_path):
    a = chats.ChatStore(tmp_path).create()
    chats.ChatStore(tmp_path).save_settings(a, model="bedrock/us.moonshotai.kimi-k3")
    assert chats.ChatStore(tmp_path).settings(a)["model"] == "bedrock/us.moonshotai.kimi-k3"


def test_turns_from_messages_keeps_user_and_assistant_text():
    messages = [{"role": "user", "content": [{"text": "hi"}]},
                {"role": "assistant", "content": [{"toolUse": {}}]},
                {"role": "user", "content": [{"toolResult": {}}]},
                {"role": "assistant", "content": [{"text": "Hello!"}]}]
    assert chats.turns_from_messages(messages) == [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "Hello!"}]
```
App tests (fake agent factory whose `messages` persist in a dict keyed by chat id): open chat after `app` re-created returns prior turns; switching `model` in a message request rebuilds the agent (factory called twice) and keeps turns; first reply emits a `title` event.
- [ ] Step 2: fail. Step 3: implement (settings in `lab11/data/chats/<id>.json`; title = first user message ≤ 40 chars; agents cached per `(chat_id, model, connectors)`). Step 4: green, commit.

### Task 4: Options and file upload

**Files:** `app.py` routes `GET /api/options`, `POST /api/chats/{id}/files`; `tests/lab11/test_options_files.py`.

- [ ] Tests: options lists the five LLMs with `available`/`reason` (bedrock: available if `boto3.Session().get_credentials()` is not None; ollama: `system1.unavailable`), four System 1 choices, connector presets; upload saves to `lab11/data/files/<id>/`, rejects `.exe` (415) and > 5 MB (413); the next message's prompt includes `Attached file: <abs path>`.
- [ ] Implement, green, commit. Add `python-multipart` to the `web` extra.

### Task 5: Connectors (MCP)

**Files:** `lab11/server/connectors.py`, routes `GET/PUT /api/connectors`, `GET /api/harness`; `tests/lab11/test_connectors.py`.

**Interfaces — Produces:** `connectors.PRESETS: dict[str, dict]` (`aws-docs` → `{"command": "uvx", "args": ["awslabs.aws-documentation-mcp-server@latest"]}`, `files` → filesystem server over the chat's file folder via `npx -y @modelcontextprotocol/server-filesystem <dir>`); `connectors.mcp_config(enabled: list[str], chat_dir: Path) -> dict`; `agents.build` passes it as `mcp_servers`; build failures from MCP are caught: the agent is rebuilt without MCP and the failure recorded as `{"id", "error"}`.
- [ ] Tests: config shape; enabling persists per chat; a factory that raises for MCP falls back and reports the error in `/api/harness`; `/api/harness` returns `tools`, `skills` (name + description from `.agent/skills/*/SKILL.md` front matter), `session` (`id, model, system1_model, messages, files`).
- [ ] Implement, green, commit.

### Task 6: Memory — watched store, recall events, graph

**Files:** `lab11/server/memory.py`, `agents.build` memory wiring, route `GET /api/memory`; `tests/lab11/test_memory.py`.

**Interfaces — Produces:** `memory.WatchedStore(FileMemoryStore)` with `on_search: Callable[[list[str]], None]`; `memory.store_for(model: str, root: Path, on_search, extract: bool = True) -> WatchedStore` (extract=False skips the model-based extractor, for tests); `memory.graph(root: Path, embed: Callable[[list[str]], list[list[float]]] | None) -> {"nodes", "links"}`; `memory.hits` counter persisted in `lab11/data/memory_hits.json`.
- [ ] Tests:
```python
import asyncio
import pytest
pytest.importorskip("fastapi")
import memory


def test_watched_store_reports_retrieved_paths(tmp_path):
    seen = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=seen.append, extract=False)
    asyncio.run(store.add("User home\nThe user lives in Dubai."))
    asyncio.run(store.search("Where does the user live? Dubai"))
    assert seen and seen[-1][0].endswith(".md")


def test_graph_links_similar_notes(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    (tmp_path / "trip.md").write_text("Trip from Dubai to Istanbul in March.")
    (tmp_path / "food.md").write_text("Likes spicy food.")
    g = memory.graph(tmp_path, embed=None)  # fallback: shared capitalised words
    assert {n["id"] for n in g["nodes"]} == {"home.md", "trip.md", "food.md"}
    assert {tuple(sorted((l["source"], l["target"]))) for l in g["links"]} == {("home.md", "trip.md")}


def test_graph_empty_folder(tmp_path):
    assert memory.graph(tmp_path, embed=None) == {"nodes": [], "links": []}
```
App test: a fake agent that calls the chat's `on_search(["home.md"])` during the stream yields `{"type": "memory", "ids": ["home.md"]}`; no search → no memory event. After each turn the server awaits `agent.memory_manager.flush()` when present.
- [ ] Implement (embeddings via Ollama `/api/embed` with `nomic-embed-text` when pulled; cosine > 0.6, top 3 per node), green, commit.

### Task 7: Web — layout, history, composer row, harness panel

**Files (all under `lab11/web/src/`):** `api.ts` (new endpoints + `memory`/`title` events), `chat.ts` (reducer handles `memory`: stores ids on the turn; `title`), `components/Sidebar.tsx`, `components/ComposerBar.tsx` (paperclip upload, LLM select, System 1 select, connectors popover), `components/HarnessPanel.tsx` (tabs: Tools, Memory, Skills, Connectors, Session, System 1), `components/Picker.tsx` (shared themed select with Lucide chevron, disabled options with reason), `App.tsx` (three columns; panel as drawer below `lg`).

- [ ] Vitest tests first: reducer stores `memory` ids and `title`; `turnsFromHistory` maps API history into turns; a stream that ends without `done` produces an error turn (move the "ended early" logic into `chat.ts` as `finishTurn(turn)` and test it).
- [ ] Implement against the contracts; sidebar groups Today / Earlier; delete uses an inline "Delete? Yes / No" row; `color-scheme: dark`; initial pickers choose the default only if available.
- [ ] `npm test && npm run build`, commit.

### Task 8: The memory globe

**Files:** `lab11/web/src/components/MemoryGlobe.tsx` (lazy-loaded), `lab11/web/src/globe.ts` (pure: `toGraph(api, firedIds) → {nodes, links}` with `fired` flags; node `val` from hits), `globe.test.ts`.

- [ ] Tests: fired ids flag their nodes and every link touching them; empty graph → empty arrays.
- [ ] Implement with `react-force-graph-3d`: dark background (transparent over the panel), node colour `#22D3EE` (fired `#6EE7B7`, emissive glow via `nodeThreeObject` sphere + `MeshBasicMaterial`), links `rgba(110,231,183,0.35)`, `linkDirectionalParticles` 4 on fired links (speed 0.01, width 2), auto-rotate camera (`controls().autoRotate = true`, speed 0.6), hover label = note text; caption "Recalled N memories" fades after 4 s; empty state "No memories yet — tell the assistant something about you".
- [ ] Refresh graph after each turn's `done`; fire on `memory` events.
- [ ] `npm test && npm run build`, commit.

### Task 9: Live check, README, PR

- [ ] Playwright on system Chrome, screenshots to the PR: (1) chat → restart server → reopen chat, history intact; (2) switch LLM mid-chat; (3) upload a `.md` itinerary and ask about it; (4) enable the AWS docs connector, its tools appear in Tools; (5) "I live in Dubai" then "What's the weather at home?" → Memory tab globe fires.
- [ ] README: replace the lab 11 section (run commands, features, screenshot of the full layout and of the globe, extending notes).
- [ ] Full test run (`uv run pytest -q`, `cd lab11/web && npm test && npm run build`), push, open PR, final review.
