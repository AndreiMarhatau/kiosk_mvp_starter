#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_SCRIPT="${ROOT_DIR}/scripts/run_backend.sh"
KIOSK_SCRIPT="${ROOT_DIR}/scripts/run_kiosk.sh"

pids=()

cleanup() {
  local exit_code=$?
  if [ ${#pids[@]} -gt 0 ]; then
    echo "Stopping child processes..."
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
      fi
    done
    wait "${pids[@]}" 2>/dev/null || true
  fi
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

echo "Ensuring application environments are ready..."
"${ROOT_DIR}/scripts/install_requirements.sh"

"${BACKEND_SCRIPT}" &
pids+=($!)

"${KIOSK_SCRIPT}" &
pids+=($!)

echo "Backend PID: ${pids[0]}"
echo "Kiosk PID: ${pids[1]}"

set +e
wait -n
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo "One of the services exited normally. Triggering shutdown."
else
  echo "One of the services exited with status ${status}. Triggering shutdown." >&2
fi

exit "$status"
