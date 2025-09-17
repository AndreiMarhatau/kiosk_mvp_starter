#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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
  return 1
}

usage() {
  cat <<'EOF'
Usage: install_requirements.sh [--backend] [--kiosk]

Without arguments the script installs the environments for both apps.
Use the flags to limit the installation to a specific app when booting them independently.
EOF
}

setup_env() {
  local app_name="$1"
  local requirements_file="$2"
  local venv_path="$3"

  echo "[${app_name}] Preparing virtual environment at ${venv_path}"

  if [ ! -d "${venv_path}" ]; then
    echo "[${app_name}] Creating virtual environment"
    "${PYTHON_BIN}" -m venv "${venv_path}"
  fi

  local venv_python
  if ! venv_python="$(resolve_venv_python "${app_name}" "${venv_path}")"; then
    exit 1
  fi
  echo "[${app_name}] Upgrading pip"
  "${venv_python}" -m pip install --upgrade pip
  echo "[${app_name}] Installing requirements from ${requirements_file}"
  "${venv_python}" -m pip install -r "${requirements_file}"
}

declare -a targets=()

while (($#)); do
  case "$1" in
    --backend)
      targets+=("backend")
      ;;
    --kiosk|--kiosk-app)
      targets+=("kiosk_app")
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [ ${#targets[@]} -eq 0 ]; then
  targets=("kiosk_app" "backend")
fi

for target in "${targets[@]}"; do
  case "$target" in
    kiosk_app)
      setup_env "kiosk_app" "${ROOT_DIR}/kiosk_app/requirements.txt" "${ROOT_DIR}/kiosk_app/.venv"
      ;;
    backend)
      setup_env "backend" "${ROOT_DIR}/backend/requirements.txt" "${ROOT_DIR}/backend/.venv"
      ;;
    *)
      echo "Unsupported target: $target" >&2
      exit 1
      ;;
  esac
done

echo "All environments are ready."