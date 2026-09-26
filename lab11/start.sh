#!/usr/bin/env bash
# Lab 11: set up and launch the Harness App with one command. Safe to run again: it skips what's done and restarts
# the app if it's already running.
#   ./lab11/start.sh          start (or restart) the app
#   ./lab11/start.sh --stop   stop it
# Assumes your models and AWS access are set up as for the other labs; the app marks anything missing.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
API_PORT=${LAB11_API_PORT:-8000}  # change these if the ports are taken
UI_PORT=${LAB11_UI_PORT:-5173}
export LAB11_API_PORT=$API_PORT  # the server listens here and the UI's dev proxy points here
OLLAMA=${OLLAMA_HOST:-http://localhost:11434}
API_LOG=lab11/server.log
UI_LOG=lab11/web.log

fail() { echo "✗ $1"; exit 1; }
trap 'echo "✗ start.sh stopped unexpectedly at line $LINENO. Run: bash -x lab11/start.sh"' ERR  # never exit silently
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 isn't installed. $2"; }

# the process listening on a port, if any
holder() { lsof -nP -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1 || true; }  # lsof fails when nothing listens
# is that process (or its parent) this app?
ours() {
  local pid=$1 parent
  parent=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  ps -o command= -p "$pid" -p "${parent:-$pid}" 2>/dev/null | grep -qE "lab11/server/app.py|$ROOT/lab11/web|lab11/web/node_modules"
}
# stop a process and the children it started (uv run and npm run each start one)
stop_tree() {
  local pid=$1
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
}
stop_running() {
  local stopped=0
  for port in "$API_PORT" "$UI_PORT"; do
    local pid
    pid=$(holder "$port")
    if [ -n "$pid" ] && ours "$pid"; then
      stop_tree "$pid"
      stopped=1
    fi
  done
  if [ "$stopped" = 1 ]; then  # wait until both ports are free again
    for _ in $(seq 1 20); do
      [ -z "$(holder "$API_PORT")" ] && [ -z "$(holder "$UI_PORT")" ] && break
      sleep 0.5
    done
    echo "→ Stopped the app that was already running"
  fi
  return 0
}

if [ "${1:-}" = "--stop" ]; then
  stop_running
  echo "Stopped."
  exit 0
fi

# ---- prerequisites -------------------------------------------------------------------------------------------
need uv "Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
need node "Install Node.js 20 or newer: https://nodejs.org"
need npm "Install Node.js 20 or newer: https://nodejs.org"
need ollama "Install Ollama: https://ollama.com/download"
node_major=$(node -p 'process.versions.node.split(".")[0]')
[ "$node_major" -ge 20 ] || fail "Node.js $(node -v) is too old; the UI needs 20 or newer: https://nodejs.org"
curl -sf "$OLLAMA/api/tags" >/dev/null || fail "Ollama isn't running at $OLLAMA. Start it: ollama serve"

# lab 11 recalls memories and knowledge by meaning with this embedding model (~270 MB, first run only)
if ! ollama list | awk 'NR > 1 {print $1}' | grep -qE '^nomic-embed-text(:latest)?$'; then
  echo "→ Pulling nomic-embed-text (first run only)…"
  ollama pull nomic-embed-text
fi

# ---- ports: restart our own app, refuse to touch anything else --------------------------------------------------
stop_running
for port in "$API_PORT" "$UI_PORT"; do
  pid=$(holder "$port")
  if [ -n "$pid" ]; then
    fail "Port $port is used by another program ($(basename "$(ps -o comm= -p "$pid")")). Pick other ports:
  LAB11_API_PORT=8001 LAB11_UI_PORT=5174 ./lab11/start.sh"
  fi
done

# ---- dependencies ----------------------------------------------------------------------------------------------
echo "→ Python dependencies"
uv sync --extra web --inexact --quiet  # --inexact: never uninstall other extras (Laya for lab 10)
STAMP=lab11/web/node_modules/.lab11-installed  # written after a successful install
if [ ! -f "$STAMP" ] || [ lab11/web/package-lock.json -nt "$STAMP" ] || [ lab11/web/package.json -nt "$STAMP" ]; then
  echo "→ Web dependencies"
  (cd lab11/web && npm install --silent)
  touch "$STAMP"
fi

# ---- start ------------------------------------------------------------------------------------------------------
API_PID=""
UI_PID=""
cleanup() {
  [ -n "$UI_PID" ] && stop_tree "$UI_PID"
  [ -n "$API_PID" ] && stop_tree "$API_PID"
}
trap 'cleanup; echo; echo "Stopped."' EXIT
trap 'exit 130' INT TERM

echo "→ Starting the API on http://127.0.0.1:$API_PORT"
uv run --extra web lab11/server/app.py > "$API_LOG" 2>&1 &
API_PID=$!
for _ in $(seq 1 90); do
  curl -sf "http://127.0.0.1:$API_PORT/api/options" >/dev/null && break
  kill -0 "$API_PID" 2>/dev/null || fail "The API stopped while starting. Last lines of $API_LOG:
$(tail -5 "$API_LOG")"
  sleep 1
done
curl -sf "http://127.0.0.1:$API_PORT/api/options" >/dev/null || fail "The API didn't answer within 90 s. See $API_LOG"

echo "→ Starting the UI on http://localhost:$UI_PORT"
(cd lab11/web && exec npm run dev -- --port "$UI_PORT" --strictPort) > "$UI_LOG" 2>&1 &
UI_PID=$!
for _ in $(seq 1 60); do
  curl -sf "http://localhost:$UI_PORT" >/dev/null && break
  kill -0 "$UI_PID" 2>/dev/null || fail "The UI stopped while starting. Last lines of $UI_LOG:
$(tail -5 "$UI_LOG")"
  sleep 1
done

# ---- check it really works: the UI must reach the API and serve its styles ---------------------------------------
through=$(curl -s "http://localhost:$UI_PORT/api/options" | head -c 20)
case "$through" in
  '{"models"'*) ;;
  *) fail "The UI isn't passing /api calls to the server on port $API_PORT. See $UI_LOG" ;;
esac
curl -s "http://localhost:$UI_PORT/src/index.css" | grep -q "tailwindcss v4" ||
  fail "The UI's styles didn't build (Tailwind). See $UI_LOG"

echo "✓ Open http://localhost:$UI_PORT   (Ctrl-C stops both; logs: $API_LOG, $UI_LOG)"
command -v open >/dev/null 2>&1 && open "http://localhost:$UI_PORT" || true
wait
