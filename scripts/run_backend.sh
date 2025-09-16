#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/backend"
VENV_PATH="${APP_DIR}/.venv"

resolve_venv_python() {
  local app_name="$1"
  local venv_path="$2"
  local candidates=(
    "${venv_path}/bin/python"
    "${venv_path}/Scripts/python"
    "${venv_path}/Scripts/python.exe"
  )

  for candidate in "${candidates[@]}"; do
    if [ -x "${candidate}" ]; then
      echo "${candidate}"
      return 0
    fi
  done

  echo "[${app_name}] Could not locate python executable in ${venv_path}" >&2
  exit 1
}

if [ ! -d "${VENV_PATH}" ]; then
  echo "[backend] Virtual environment not found. Installing requirements..."
  "${ROOT_DIR}/scripts/install_requirements.sh" --backend
fi

PYTHON_EXEC="${PYTHON_BIN:-}"
if [ -z "${PYTHON_EXEC}" ]; then
  PYTHON_EXEC="$(resolve_venv_python "backend" "${VENV_PATH}")"
fi

cd "${APP_DIR}"

APP_MODULE="${APP_MODULE:-app.main:app}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
ENABLE_RELOAD="${ENABLE_RELOAD:-1}"

ARGS=("${PYTHON_EXEC}" "-m" "uvicorn" "${APP_MODULE}" "--host" "${HOST}" "--port" "${PORT}")
if [ "${ENABLE_RELOAD}" != "0" ]; then
  ARGS+=("--reload")
fi

exec "${ARGS[@]}"
