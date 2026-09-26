#!/usr/bin/env bash
# Run Kev (an open Jev-alike) on this machine for labs 6b, 6e-10.
# It keeps running in the background, so only the first lab waits for it.
#   ./kev.sh start | stop | status
set -euo pipefail
cd "$(dirname "$0")"

PORT="${KEV_PORT:-8009}"
MODEL="${KEV_MODEL:-jaredpalmer/kev-4b}"  # needs a 32 GB Mac; jaredpalmer/kev-0.8b runs on any Apple Silicon
PIDFILE=.kev/kev.pid
LOG=.kev/kev.log

up() { curl -s -o /dev/null "http://127.0.0.1:$PORT"; }

case "${1:-start}" in
  start)
    if up; then echo "Kev is already running on port $PORT."; exit 0; fi
    mkdir -p .kev
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Kev is already starting — waiting for it (no second copy)."
    else
      echo "Starting Kev ($MODEL) on port $PORT. The first start downloads it (~9 GB); after that about a minute."
      # uv fetches Kev from GitHub: no clone, no install step.
      nohup uv run --no-project --python 3.13 --with "kev[serve] @ git+https://github.com/jaredpalmer/kev" \
        python -m kev.serve --run "$MODEL" --port "$PORT" > "$LOG" 2>&1 &
      echo $! > "$PIDFILE"
    fi
    until up; do
      if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then echo; echo "Kev didn't start. See $LOG"; exit 1; fi
      printf "."; sleep 2
    done
    echo " ready. It keeps running; stop it with: ./kev.sh stop"
    ;;
  stop)
    if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
      rm -f "$PIDFILE"; echo "Kev stopped."
    else
      echo "Kev isn't running (or wasn't started by ./kev.sh)."
    fi
    ;;
  status)
    if up; then echo "Kev is running on port $PORT."; else echo "Kev is not running."; fi
    ;;
  *) echo "usage: ./kev.sh [start|stop|status]"; exit 1 ;;
esac
