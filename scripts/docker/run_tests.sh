#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$WORKSPACE_DIR"

docker compose run --rm dev bash -lc '
  cd "$ROS2_WS_AI_ROOT" &&
  colcon build --symlink-install &&
  cd src/sutradhara_orchestrator &&
  if [[ -x .venv/bin/python ]]; then
    .venv/bin/python -m pytest tests -q
  else
    python3 -m pytest tests -q
  fi
'
