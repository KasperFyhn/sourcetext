#!/bin/bash
# Run a mock-data scenario (API on :8001) together with the hot-reloading Vite dev server (UI on :3000).
# Usage: [SOURCETEXT_API_PORT=8001] ./scripts/dev.sh <scenario>   (see dev/scenarios/)

set -e
export SOURCETEXT_API_PORT="${SOURCETEXT_API_PORT:-8001}"
trap 'kill $(jobs -p) 2>/dev/null' EXIT

python dev/serve.py "${1:?usage: ./scripts/dev.sh <scenario>}" --port "$SOURCETEXT_API_PORT" --dev &
npm --prefix ui run dev &
wait
