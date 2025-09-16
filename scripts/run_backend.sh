#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/backend"
VENV_PATH="${APP_DIR}/.venv"

if [ ! -d "${VENV_PATH}" ]; then
  echo "[backend] Virtual environment not found. Installing requirements..."
  "${ROOT_DIR}/scripts/install_requirements.sh"
fi

# shellcheck disable=SC1090
source "${VENV_PATH}/bin/activate"

cd "${APP_DIR}"

APP_MODULE="${APP_MODULE:-app.main:app}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
ENABLE_RELOAD="${ENABLE_RELOAD:-1}"

ARGS=("python" "-m" "uvicorn" "${APP_MODULE}" "--host" "${HOST}" "--port" "${PORT}")
if [ "${ENABLE_RELOAD}" != "0" ]; then
  ARGS+=("--reload")
fi

exec "${ARGS[@]}"
