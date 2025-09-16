#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/kiosk_app"
VENV_PATH="${APP_DIR}/.venv"

if [ ! -d "${VENV_PATH}" ]; then
  echo "[kiosk_app] Virtual environment not found. Installing requirements..."
  "${ROOT_DIR}/scripts/install_requirements.sh"
fi

# shellcheck disable=SC1090
source "${VENV_PATH}/bin/activate"

PYTHON_BIN="${PYTHON_BIN:-python}"
APP_ENTRY="${APP_ENTRY:-${APP_DIR}/main.py}"

exec "${PYTHON_BIN}" "${APP_ENTRY}"
