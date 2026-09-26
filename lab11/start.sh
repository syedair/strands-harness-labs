#!/usr/bin/env bash
# Lab 11: set up and launch the Harness App with one command. Safe to run again: it skips what's already done.
#   ./lab11/start.sh
# Assumes your models and AWS access are set up as for the other labs; the app marks anything missing.
set -euo pipefail
cd "$(dirname "$0")/.."
API_PORT=${LAB11_API_PORT:-8000}  # change these if the ports are taken
UI_PORT=${LAB11_UI_PORT:-5173}
export LAB11_API_PORT=$API_PORT  # the server listens here and the UI's dev proxy points here

fail() { echo "✗ $1"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 isn't installed. $2"; }

need uv "Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
need npm "Install Node.js 20 or newer: https://nodejs.org"
need ollama "Install Ollama: https://ollama.com/download"
curl -sf http://localhost:11434/api/tags >/dev/null || fail "Ollama isn't running. Start it: ollama serve"

# lab 11 recalls memories and knowledge by meaning with this embedding model (~270 MB, first run only)
if ! ollama list | awk 'NR > 1 {print $1}' | grep -qE '^nomic-embed-text(:latest)?$'; then
  echo "→ Pulling nomic-embed-text (first run only)…"
  ollama pull nomic-embed-text
fi

for port in "$API_PORT" "$UI_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "Port $port is in use. Is the app already running? Stop it, or open http://localhost:$UI_PORT"
  fi
done

echo "→ Python dependencies"
uv sync --extra web --quiet
if [ ! -d lab11/web/node_modules ]; then
  echo "→ Web dependencies (first run only)"
  (cd lab11/web && npm install --silent)
fi

echo "→ Starting the API on http://127.0.0.1:$API_PORT"
uv run --extra web lab11/server/app.py > lab11/server.log 2>&1 &
API_PID=$!
trap 'kill $API_PID ${UI_PID:-} 2>/dev/null; echo; echo "Stopped."' EXIT INT TERM
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$API_PORT/api/options" >/dev/null && break
  kill -0 "$API_PID" 2>/dev/null || fail "The API didn't start. See lab11/server.log"
  sleep 1
done

echo "→ Starting the UI"
(cd lab11/web && npm run dev -- --port "$UI_PORT" --strictPort >/dev/null 2>&1) &
UI_PID=$!
for _ in $(seq 1 30); do curl -sf "http://localhost:$UI_PORT" >/dev/null && break; sleep 1; done

echo "✓ Open http://localhost:$UI_PORT   (Ctrl-C stops both; API log: lab11/server.log)"
command -v open >/dev/null 2>&1 && open "http://localhost:$UI_PORT" || true
wait
