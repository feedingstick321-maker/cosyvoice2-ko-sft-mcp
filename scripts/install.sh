#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
TORCH_BACKEND="${TORCH_BACKEND:-cu128}"
VENV="${REPO_ROOT}/.venv"
PYTHON_EXE="${VENV}/bin/python"

command -v uv >/dev/null 2>&1 || {
  echo "uv is required: https://docs.astral.sh/uv/" >&2
  exit 1
}

uv venv --python "${PYTHON_VERSION}" "${VENV}"
if [[ "${TORCH_BACKEND}" == "cpu" ]]; then
  uv pip install --python "${PYTHON_EXE}" torch==2.8.0 torchaudio==2.8.0 \
    --index-url https://download.pytorch.org/whl/cpu
else
  uv pip install --python "${PYTHON_EXE}" torch==2.8.0 torchaudio==2.8.0 \
    --index-url https://download.pytorch.org/whl/cu128
fi
uv pip install --python "${PYTHON_EXE}" setuptools wheel
uv pip install --python "${PYTHON_EXE}" --no-build-isolation --no-deps openai-whisper==20231117
uv pip install --python "${PYTHON_EXE}" -r "${REPO_ROOT}/requirements_mcp.txt"
uv pip install --python "${PYTHON_EXE}" --editable "${REPO_ROOT}"

echo "Installed. Next: ${VENV}/bin/cosyvoice-ko-prepare"
