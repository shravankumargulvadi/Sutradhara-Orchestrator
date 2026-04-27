#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$WORKSPACE_DIR"

run_args=(run --rm)
launch_args=()
xhost_granted=0

cleanup() {
  if [[ "$xhost_granted" -eq 1 ]] && command -v xhost >/dev/null 2>&1; then
    xhost -SI:localuser:root >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

if [[ -n "${DISPLAY:-}" ]]; then
  host_xauthority="${XAUTHORITY:-$HOME/.Xauthority}"

  if command -v xhost >/dev/null 2>&1; then
    if xhost +SI:localuser:root >/dev/null 2>&1; then
      xhost_granted=1
    else
      echo "Warning: failed to grant X server access to local root; Gazebo GUI may still fail." >&2
    fi
  fi

  run_args+=(
    -e "DISPLAY=$DISPLAY"
    -e "XAUTHORITY=/root/.Xauthority"
  )

  if [[ -f "$host_xauthority" ]]; then
    run_args+=(
      -v "$host_xauthority:/root/.Xauthority:ro"
    )
  else
    echo "DISPLAY is set but XAUTHORITY file was not found at $host_xauthority; trying X host access without it." >&2
  fi

  launch_args+=(headless:=false)
fi

docker compose "${run_args[@]}" sim bash -lc "
  cd \"\$ROS2_WS_AI_ROOT\" &&
  ros2 launch inspection_sim inspection_multi_robot_demo.launch.py ${launch_args[*]:-}
"
