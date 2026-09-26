# Lab 11: The Harness App — Design (v2)

## Purpose

The finale: the finished travel assistant as a full web app that shows everything the Strands
Harness gives you — sessions, memory, skills, tools, MCP connectors, model choice — and the
System 1 decisions that guard it. It is an example to extend, not a product: local, single
user, no auth, no deployment.

v1 (committed on this branch) showed only System 1. v2 keeps its streaming, reducer, theme and
decision chips, and grows it into the app below.

## Decisions (agreed 2026-09-26)

- **Own folder:** `lab11/server/` (Python, FastAPI) and `lab11/web/` (React + Vite + TypeScript
  + Tailwind 4 + lucide-react icons). The agent stays in Python.
- **Look:** ContentCreationKit theme `developer-studio`, preset Default (tokens unchanged from
  v1: `#0B1120 → #0E1A2B`, accent `#6EE7B7`, accent-2 `#22D3EE`, text `#F8FAFC`/66%, SF Pro /
  SF Mono labels, no default blue, no Roboto, one `.tint` surface per screen = the composer).
  Lucide icons only, no emoji. Buttons have hover, press (`scale 0.95`) and accent focus states;
  waiting states: Thinking (dots), Running &lt;tool&gt; (spinner), writing cursor.
- **Memory globe:** the Memory tab is a rotating 3D network of memory notes; notes retrieved
  for the current turn light up and their links fire.

## Layout

```
┌ Sidebar ──────┬ Chat ─────────────────────────────────┬ Inside the harness ────────────┐
│ + New chat    │ messages, tool cards, decision chips   │ [Tools][Memory][Skills]        │
│ Today         │                                        │ [Connectors][Session][System 1]│
│  Paris trip   │                                        │                                │
│  Istanbul …   │                                        │  (Memory = 3D globe)           │
│ Earlier       │ ┌ composer (.tint) ──────────────────┐ │                                │
│  …            │ │ 📎  Ask about a trip…          Send │ │                                │
│               │ │ LLM ▾  · System 1 ▾ · ＋ Connectors │ │                                │
└───────────────┴─┴────────────────────────────────────┴─┴────────────────────────────────┘
```

(The picture uses symbols for layout only; the UI uses Lucide icons.)

- **Sidebar — chat history.** Chats listed newest first with a title (the first user message,
  shortened) and relative time; New chat; open a past chat; delete (inline two-step confirm, no
  browser dialog). Chats are harness sessions saved to disk, so they survive a server restart.
- **Composer row:** attach files (paperclip), LLM picker, System 1 picker, Connectors (+).
- **Inside the harness panel**, tabs:
  - **Tools** — the agent's live tool list (built-in, skills, memory, MCP), each with its source.
  - **Memory** — the globe (below) and a list of notes.
  - **Skills** — skills found in `.agent/skills`, with their description.
  - **Connectors** — MCP servers: enabled/disabled, status, the tools each adds.
  - **Session** — chat id, model, System 1 model, message count, files in the workspace.
  - **System 1** — every gate and check decision in this chat, newest first.
- Narrow screens: the panel becomes a drawer toggled from the header.

## Harness features and how the app uses them

| Feature | How |
|---|---|
| Sessions / chat history | `create_harness(session={"id": chat_id, "dir": lab11/data/sessions})`; reopening a chat rebuilds the agent with the same id and the harness restores `agent.messages`, which the API converts to turns. |
| LLM choice | `model=` one of the `.env`-style strings (Kimi K2.5 default, Nemotron, Claude Sonnet 5, Kimi K3, `ollama/gpt-oss:20b`). The list shows only models whose provider is reachable. Changing it mid-chat rebuilds the agent on the same session id. |
| System 1 | As v1: `config.SYSTEM1_MODEL` per request; lab 7's gate (web_fetch only) and lab 8's check, subclassed to emit events. |
| Files | Upload saves to `lab11/data/files/<chat_id>/`; the next message tells the agent the file's absolute path; it reads it with the built-in `read` tool. Text-like files (txt, md, csv, json, pdf via harness read support) up to 5 MB. |
| Connectors (MCP) | `mcp_servers={...}` in the standard `mcpServers` shape. Presets: AWS Documentation MCP (`uvx awslabs.aws-documentation-mcp-server@latest`) and a filesystem server scoped to the chat's file folder; plus custom command. Saved in `lab11/data/connectors.json`; enabling one rebuilds the chat's agent. |
| Memory | `memory={"stores": [WatchedStore(FileMemoryStore(lab11/data/memory))]}`; `WatchedStore` delegates everything and records each `search` result, so the app knows which notes were retrieved this turn (both automatic injection and the `search_memory` tool). After each turn the server flushes memory extraction so new notes appear. |
| Skills | `skills=True` (the packing-list skill from lab 4). |
| Tools | `agent.tool_names` (plus MCP tools), shown in the Tools tab. |

## The memory globe

- **Nodes:** one per memory note, glowing spheres sized by how often the note has been retrieved.
- **Links:** between semantically similar notes — cosine similarity of embeddings from Ollama's
  `nomic-embed-text` (above a threshold, top 3 per node); if the embedding model isn't pulled,
  notes that share a capitalised word (a place, a name) are linked instead.
- **Motion:** slow auto-rotation; drag to orbit, scroll to zoom, hover shows the note text.
- **Firing:** when a turn retrieves notes, those nodes pulse in the accent colour and their links
  carry travelling particles for a few seconds; a caption says "Recalled 2 memories".
- Library: `react-force-graph-3d` (three.js), loaded only when the Memory tab opens.

## API (`lab11/server`)

- `GET /api/options` → LLM models, System 1 models (with availability and fix), connector presets.
- `GET /api/chats` → `[{id, title, updated_at}]`; `POST /api/chats` → new id; `DELETE /api/chats/{id}`.
- `GET /api/chats/{id}` → `{turns, model, system1_model, files, connectors}`.
- `POST /api/chats/{id}/messages` `{message, model, system1_model}` → NDJSON events:
  `text`, `tool`, `decision` (with `why`, `p`, `probs`), `memory` (`{"ids": [...]}` retrieved this
  turn), `title` (first turn), `done`, `error`. The stream always ends with `done` or `error`.
- `POST /api/chats/{id}/files` (multipart) → `{name, path, size}`.
- `GET/PUT /api/connectors` → saved MCP servers with enabled flags.
- `GET /api/harness?chat_id=` → `{tools, skills, session}`.
- `GET /api/memory` → `{nodes: [{id, text, hits}], links: [{source, target, weight}]}`.

## Fixes carried from the v1 review

- The gate and check get the **current** user message and reset their counters at the start of
  every turn (v1 judged later turns against the first message and let caps run out per chat).
- The UI ends a turn that stops without `done`/`error` with an error, re-enabling the composer.
- Server tests skip cleanly when the `web` extra isn't installed (`pytest.importorskip`).
- Lab 8's "reply ends with a question" rule prints `[check] -> Proceed (asked the user a question)`
  and is described in the README.
- Deny decisions keep their rule; events recorded before an error are sent before it; the
  initial pickers never land on an unavailable option; `color-scheme: dark` for native controls.

## Errors

Every endpoint returns a JSON error with a one-line fix; the chat stream ends with an `error`
event. Unavailable LLM / System 1 / connector → disabled in its picker with the fix as a tooltip.
An MCP server that fails to start → its connector shows "failed" with the first line of the error,
and the chat keeps working without it.

## Testing

- Server (FastAPI `TestClient`, fake agents): chat CRUD round trip; history survives a new app
  instance; two-turn chat judges the second message; memory event carries retrieved ids; file
  upload size/type limits; connectors persisted; stream always terminates.
- `WatchedStore` unit test with a fake inner store; memory graph builder test (embedding and
  fallback paths).
- Web (Vitest): reducer incl. `memory` and `title` events; stream-ended-early handling; globe
  data mapping (retrieved ids → highlighted nodes/links).
- `npm run build` type-checks.
- Live check with Playwright on system Chrome: history across a server restart, model switch
  mid-chat, file upload read back, a connector's tools appearing, the memory globe firing on
  "what's the weather at home?" after "I live in Dubai". Screenshots in the PR.

## Out of scope

Auth, multiple users, deployment, editing memory notes from the UI, lab 9's router.
