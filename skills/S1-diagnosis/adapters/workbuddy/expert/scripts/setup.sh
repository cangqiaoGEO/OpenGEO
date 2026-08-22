#!/usr/bin/env bash
set -euo pipefail

EXPERT_ROOT="${CODEBUDDY_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
bash "${EXPERT_ROOT}/skills/geo-browser-runtime/scripts/ensure_runtime.sh"
