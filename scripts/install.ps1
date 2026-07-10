[CmdletBinding()]
param(
    [string]$Python = "3.10",
    [ValidateSet("cu128", "cpu")]
    [string]$TorchBuild = "cu128"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot ".venv"
$PythonExe = Join-Path $Venv "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found. Install it from https://docs.astral.sh/uv/"
}

uv venv --python $Python $Venv
if ($TorchBuild -eq "cpu") {
    uv pip install --python $PythonExe torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
} else {
    uv pip install --python $PythonExe torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
}
uv pip install --python $PythonExe setuptools wheel
uv pip install --python $PythonExe --no-build-isolation --no-deps openai-whisper==20231117
uv pip install --python $PythonExe -r (Join-Path $RepoRoot "requirements_mcp.txt")
uv pip install --python $PythonExe --editable $RepoRoot

Write-Host "Installed local MCP environment: $Venv"
Write-Host "Next: $Venv\Scripts\cosyvoice-ko-prepare.exe"
