#!/usr/bin/env bash
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

install_agent_browser() {
  if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || -n "${WINDIR:-}" ]]; then
    local windows_installer="${SKILL_ROOT}/scripts/install-windows.ps1"
    if command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$windows_installer"
    elif command -v powershell >/dev/null 2>&1; then
      powershell -NoProfile -ExecutionPolicy Bypass -File "$windows_installer"
    else
      echo "PowerShell is required to install agent-browser on Windows" >&2
      return 1
    fi
    return
  fi

  if ! command -v npm >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
    echo "Node.js 18+ and npm are required before GEO browser collection" >&2
    return 1
  fi

  local node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]')"
  if (( node_major < 18 )); then
    echo "Node.js 18+ is required, current version: $(node --version)" >&2
    return 1
  fi

  echo "Installing agent-browser CLI"
  npm install -g agent-browser
  echo "Installing agent-browser browser runtime"
  agent-browser install
}

if ! command -v agent-browser >/dev/null 2>&1; then
  install_agent_browser
fi

if ! agent-browser doctor; then
  echo "Repairing agent-browser browser runtime"
  agent-browser install
  agent-browser doctor
fi

echo "GEO browser runtime is ready"
