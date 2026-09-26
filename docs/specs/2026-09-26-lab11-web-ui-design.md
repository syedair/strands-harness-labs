# Lab 11: Web Chat UI — Design

## Purpose

The finale of the series: an example of how to put a Strands Harness agent behind a web
application. The finished travel assistant (labs 1–8) is served by a small Python API and
used through a polished React chat UI that shows the System 1 decisions as they happen.
It is an example to extend, not a product: local, single user, no auth, no deployment.

## Decisions (agreed 2026-09-26)

- **Agent stays in Python.** The UI is a window onto the same harness code; nothing is
  ported to TypeScript. Streamlit was rejected.
- **React + Vite + TypeScript + Tailwind** for the UI.
- **Look: ContentCreationKit theme `developer-studio`, preset Default** — charcoal-navy
  backdrop (`#0B1120 → #0E1A2B`), restrained glass lit top-left, accent `#6EE7B7`,
  secondary `#22D3EE`, text `#F8FAFC` / 66%, SF Pro Display/Text with SF Mono uppercase
  labels (0.18em tracking). Theme rules kept: no default blue, no Roboto, one `.tint`
  (accent-tinted) surface per screen. Tokens are copied as CSS variables into
  `web/src/theme.css`; Tailwind reads them.
- **System 1 model dropdown** in the header: Qwen stand-in / Jev / Kev / Laya. Backends
  that can't run are shown disabled with the one-line fix (from `system1.unavailable()`).
- **Left out on purpose:** lab 9's router, logins, multiple users, deployment.

## Architecture

```
web/ (React, :5173)  ──POST /api/chat (NDJSON stream)──▶  labs/lab11_web/server.py (FastAPI, :8000)
                      ◀──GET  /api/system1──────────────      └─ create_harness(...) per session
                                                               ├─ ToolCallGate    (from lab 7)
                                                               └─ CompletionCheck (from lab 8)
```

### Server — `labs/lab11_web/server.py` (~80 lines)

- One harness agent per `session_id`, kept in memory. Same settings as the finished
  assistant: `builtin_tools=["web_fetch"]`, `memory=True`, `skills=True`, and
  `interventions=[gate, check]` where the gate and check are lab 7's `ToolCallGate` and
  lab 8's `CompletionCheck`, subclassed only to also emit events (below).
- `GET /api/system1` → `[{id, label, available, reason}]` for `ollama/qwen3.5:4b`, `jev`,
  `kev`, `laya`.
- `POST /api/chat {session_id, message, system1_model}` → a newline-delimited JSON stream:
  - `{"type": "text", "delta": "..."}` — reply text as it streams
  - `{"type": "tool", "name": "web_fetch", "input": {...}}` — the agent calls a tool
  - `{"type": "decision", "source": "gate" | "check", "action": "guide" | "deny" | "proceed", "summary": "...", "probs": {...}}`
  - `{"type": "done"}` or `{"type": "error", "message": "..."}`
- The selected System 1 model applies to the request by setting `config.SYSTEM1_MODEL`
  before the agent runs (single local user, so a process-wide setting is acceptable).
- Run: `uv run labs/lab11_web/server.py` (uvicorn on 127.0.0.1:8000). New dependencies:
  `fastapi`, `uvicorn` (in an optional `web` extra).

### Decision events — minimal change to labs 7 and 8

Lab 7's gate and lab 8's check each store their last probabilities on `self` (one line
each). Lab 11 subclasses them and, after calling the parent, emits a `decision` event with
the returned action and those probabilities. Labs 7 and 8 behave and print exactly as today.

### UI — `web/`

- **Header:** "Travel assistant" title, mono eyebrow "STRANDS HARNESS · SYSTEM 1", the
  System 1 dropdown, and a "New chat" button (new `session_id`).
- **Messages:** user bubbles right; assistant replies left on glass panels, text streaming in.
- **Tool calls:** a compact card inside the assistant reply (`web_fetch · wttr.in/Paris`).
- **Decision chips** under the reply, one per decision:
  - gate guide/deny → amber, "🛡 Gate blocked Seattle · P(city named) 0.34"
  - gate proceed → accent, "🛡 Gate allowed Paris · 0.94"
  - check → "✓ Completion check · 0.78" or "↻ Sent back to finish · 0.16"
- **Composer:** textarea, Enter sends, Shift+Enter newline; disabled while streaming.
- **Empty state:** three suggestion chips ("What's the weather?", "Weather in Paris?",
  "Pack for 4 days in Istanbul") that demo the gate, a clean call, and the skill.
- Streaming is read with `fetch` + a `ReadableStream` line reader (no extra library).
- Run: `cd web && npm install && npm run dev`; Vite proxies `/api` to :8000.

## Errors

- Server errors mid-stream → an `error` event; the UI shows it inline in the reply.
- Unavailable System 1 backend → disabled in the dropdown with its fix; selecting it is not
  possible. If it becomes unavailable mid-session, the request returns an `error` event.
- API down → the UI shows "Start the server: uv run labs/lab11_web/server.py".

## Testing

- `tests/test_lab11_server.py` with FastAPI's `TestClient` and a fake agent: the NDJSON
  stream contains text, tool and decision events in order; `/api/system1` reports
  availability from `system1.unavailable`; a new `session_id` gets a new agent.
- Labs 7 and 8: existing tests stay green; one test each that `last_probs` is recorded.
- UI: `npm run build` must pass (type check). Then a live browser check of a full
  conversation (guessed city blocked → asks → Paris allowed → packing list), on the
  Qwen stand-in and on Jev, with screenshots.

## README

A "Lab 11: Web Chat UI" section: how to run both halves, a screenshot, and "extending it":
where to add endpoints, how events flow, and how to swap the UI framework.
