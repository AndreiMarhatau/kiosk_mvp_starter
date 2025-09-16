#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_SCRIPT="${ROOT_DIR}/scripts/run_backend.sh"
KIOSK_SCRIPT="${ROOT_DIR}/scripts/run_kiosk.sh"

pids=()
supports_wait_n=0

if [[ "${BASH_VERSINFO[0]:-0}" -gt 4 ]] ||
   ([[ "${BASH_VERSINFO[0]:-0}" -eq 4 ]] && [[ "${BASH_VERSINFO[1]:-0}" -ge 3 ]]); then
  supports_wait_n=1
fi

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

(
  unset -v PYTHON_BIN PYTHONPATH PYTHONHOME
  exec "${BACKEND_SCRIPT}"
) &
pids+=($!)

(
  unset -v PYTHON_BIN PYTHONPATH PYTHONHOME
  exec "${KIOSK_SCRIPT}"
) &
pids+=($!)

echo "Backend PID: ${pids[0]}"
echo "Kiosk PID: ${pids[1]}"

set +e
if [ "${supports_wait_n}" -eq 1 ]; then
  wait -n
  status=$?
else
  status=0
  finished=0
  while [ "$finished" -eq 0 ]; do
    for pid in "${pids[@]}"; do
      if ! kill -0 "$pid" 2>/dev/null; then
        wait "$pid" 2>/dev/null
        status=$?
        finished=1
        break
      fi
    done
    if [ "$finished" -eq 0 ]; then
      sleep 1
    fi
  done
fi
set -e

if [ "$status" -eq 0 ]; then
  echo "One of the services exited normally. Triggering shutdown."
else
  echo "One of the services exited with status ${status}. Triggering shutdown." >&2
fi

exit "$status"
