#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

setup_env() {
  local app_name="$1"
  local requirements_file="$2"
  local venv_path="$3"

  echo "[${app_name}] Preparing virtual environment at ${venv_path}"

  if [ ! -d "${venv_path}" ]; then
    echo "[${app_name}] Creating virtual environment"
    "${PYTHON_BIN}" -m venv "${venv_path}"
  fi

  # shellcheck disable=SC1090
  source "${venv_path}/bin/activate"
  echo "[${app_name}] Upgrading pip"
  python -m pip install --upgrade pip
  echo "[${app_name}] Installing requirements from ${requirements_file}"
  python -m pip install -r "${requirements_file}"
  deactivate
}

setup_env "kiosk_app" "${ROOT_DIR}/kiosk_app/requirements.txt" "${ROOT_DIR}/kiosk_app/.venv"
setup_env "backend" "${ROOT_DIR}/backend/requirements.txt" "${ROOT_DIR}/backend/.venv"

echo "All environments are ready."
