#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/kiosk_app"
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
  echo "[kiosk_app] Virtual environment not found. Installing requirements..."
  "${ROOT_DIR}/scripts/install_requirements.sh" --kiosk
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "${PYTHON_BIN}" ]; then
  PYTHON_BIN="$(resolve_venv_python "kiosk_app" "${VENV_PATH}")"
fi
APP_ENTRY="${APP_ENTRY:-${APP_DIR}/main.py}"

exec "${PYTHON_BIN}" "${APP_ENTRY}"
