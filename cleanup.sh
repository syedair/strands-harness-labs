#!/usr/bin/env bash
# Undo what the labs set up on this machine: stop Kev, clear lab state, and (only if you say y)
# delete the models they downloaded. ./reset.sh only clears state; this also frees disk space.
set -uo pipefail
cd "$(dirname "$0")"

exec 3<&0  # keep your answers separate from the lists we loop over
ask() { read -r -p "$1 [y/N] " answer <&3; [[ "$answer" =~ ^[Yy] ]]; }

./kev.sh stop
./reset.sh
rm -rf .kev

if [ -d lab11/data ]; then
  ask "Delete lab 11's chats, files and memories (lab11/data)?" && rm -rf lab11/data
fi

echo
echo "Downloads — each one is kept unless you answer y (you may use these models elsewhere):"

# Ollama models the labs use
if command -v ollama >/dev/null; then
  ollama list 2>/dev/null | awk 'NR>1 {print $1, $3, $4}' | while read -r name size unit; do
    case "$name" in
      qwen3.5:4b|qwen3.5:9b|gpt-oss:20b)
        ask "Delete Ollama model $name ($size $unit)?" && ollama rm "$name" ;;
    esac
  done
fi

# Hugging Face models: Kev's adapter, Kev's Qwen base model, Laya
uvx -q --from huggingface_hub hf cache ls 2>/dev/null \
  | grep -E '^model/(jaredpalmer/kev-|Qwen/Qwen3\.5-.*-Base|convaiinnovations/laya)' \
  | awk '{print $1, $2}' | while read -r repo size; do
      ask "Delete Hugging Face model ${repo#model/} ($size)?" \
        && uvx -q --from huggingface_hub hf cache rm "$repo" --yes >/dev/null && echo "  deleted"
    done

if [ -d .venv ]; then
  ask "Delete this repo's Python environment (.venv, $(du -sh .venv | cut -f1))? uv sync recreates it." \
    && rm -rf .venv
fi
echo "Done."
