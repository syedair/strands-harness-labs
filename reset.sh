#!/usr/bin/env bash
# Clear what the labs remember so the next take starts fresh.
# Keeps .agent/skills (the packing-list skill is part of the repo).
set -euo pipefail
cd "$(dirname "$0")"

rm -rf .agent/sessions .agent/memory trips
echo "Cleared: .agent/sessions .agent/memory trips"
