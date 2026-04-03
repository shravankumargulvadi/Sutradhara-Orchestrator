#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$WORKSPACE_DIR"

run_args=(run --rm)
launch_args=()

if [[ -n "${DISPLAY:-}" ]]; then
  host_xauthority="${XAUTHORITY:-$HOME/.Xauthority}"

  if [[ -f "$host_xauthority" ]]; then
    run_args+=(
      -e "DISPLAY=$DISPLAY"
      -e "XAUTHORITY=/root/.Xauthority"
      -v "$host_xauthority:/root/.Xauthority:ro"
    )
    launch_args+=(headless:=false)
  else
    echo "DISPLAY is set but XAUTHORITY file was not found at $host_xauthority; falling back to headless Gazebo." >&2
  fi
fi

docker compose "${run_args[@]}" sim bash -lc "
  cd \"\$ROS2_WS_AI_ROOT\" &&
  ros2 launch inspection_sim inspection_uav_demo.launch.py ${launch_args[*]:-}
"
