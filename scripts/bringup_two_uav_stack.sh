#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${ROS2_WS_AI_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
UNDERLAY_INSTALL="${UNDERLAY_INSTALL:-/opt/underlay_ws/install}"
XRCE_INSTALL="${XRCE_INSTALL:-/opt/xrce_ws/install}"
PX4_DIR="${PX4_DIR:-/opt/px4}"
PX4_BIN="${PX4_BIN:-$PX4_DIR/build/px4_sitl_default/bin/px4}"
PX4_DATA_PATH="${PX4_DATA_PATH:-$PX4_DIR/build/px4_sitl_default/etc}"
PX4_ROOTFS_BASE="${PX4_ROOTFS_BASE:-$PX4_DIR/build/px4_sitl_default/rootfs}"
MICRO_XRCE_AGENT_BIN_DEFAULT="${MICRO_XRCE_AGENT_BIN:-$XRCE_INSTALL/microxrcedds_agent/bin/MicroXRCEAgent}"

FLIGHT_ALTITUDE_M="${FLIGHT_ALTITUDE_M:-8.0}"
WAIT_FOR_TOPICS_SEC="${WAIT_FOR_TOPICS_SEC:-60}"
WAIT_BEFORE_READY_SEC="${WAIT_BEFORE_READY_SEC:-20}"
UAV2_MODEL_POSE="${UAV2_MODEL_POSE:-0,3}"
PX4_AUTOSTART="${PX4_AUTOSTART:-4001}"
LOG_ROOT="$WORKSPACE_DIR/test_logs/$(date +%Y%m%d_%H%M%S)_bringup"

declare -a PIDS=()

source_setup() {
  set +u
  # shellcheck disable=SC1090
  source "$1"
  set -u
}

cleanup() {
  local pid
  echo
  echo "Cleaning up background processes..."
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  sleep 2

  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT INT TERM

resolve_micro_xrce_agent() {
  if [[ -x "$MICRO_XRCE_AGENT_BIN_DEFAULT" ]]; then
    echo "$MICRO_XRCE_AGENT_BIN_DEFAULT"
    return 0
  fi

  if command -v MicroXRCEAgent >/dev/null 2>&1; then
    command -v MicroXRCEAgent
    return 0
  fi

  return 1
}

wait_for_topic() {
  local topic="$1"
  local timeout="$2"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    if ros2 topic list | grep -qx "$topic"; then
      return 0
    fi

    if (( "$(date +%s)" - start_ts >= timeout )); then
      echo "Timed out waiting for topic: $topic" >&2
      return 1
    fi

    sleep 1
  done
}

start_bg() {
  local name="$1"
  local logfile="$2"
  shift 2

  "$@" >"$logfile" 2>&1 &
  PIDS+=("$!")
  echo "Started $name (pid ${PIDS[-1]}), log: $logfile"
}

if pgrep -f "MicroXRCEAgent udp4 -p 8888" >/dev/null 2>&1; then
  echo "MicroXRCEAgent already appears to be running. Stop existing test processes first." >&2
  exit 1
fi

if pgrep -f "$PX4_BIN -i 1" >/dev/null 2>&1 || pgrep -f "$PX4_BIN -i 2" >/dev/null 2>&1; then
  echo "PX4 SITL instance 1 or 2 is already running. Stop existing instances first." >&2
  exit 1
fi

if [[ ! -x "$PX4_BIN" ]]; then
  echo "Missing PX4 SITL binary at $PX4_BIN" >&2
  echo "Build PX4 first, then rerun this script." >&2
  exit 1
fi

if ! command -v ros2 >/dev/null 2>&1; then
  echo "Missing required command: ros2" >&2
  exit 1
fi

mkdir -p "$LOG_ROOT"

source_setup /opt/ros/jazzy/setup.bash
source_setup "$UNDERLAY_INSTALL/setup.bash"
source_setup "$WORKSPACE_DIR/install/setup.bash"
if [[ -f "$XRCE_INSTALL/setup.bash" ]]; then
  source_setup "$XRCE_INSTALL/setup.bash"
fi

if ! MICRO_XRCE_AGENT_BIN="$(resolve_micro_xrce_agent)"; then
  echo "Could not find MicroXRCEAgent in $MICRO_XRCE_AGENT_BIN_DEFAULT or on PATH" >&2
  exit 1
fi

echo "Logs will be written under: $LOG_ROOT"
echo "Using UAV2 model pose: $UAV2_MODEL_POSE"
echo "Using MicroXRCEAgent binary: $MICRO_XRCE_AGENT_BIN"

start_bg "MicroXRCEAgent" "$LOG_ROOT/xrce_agent.log" \
  "$MICRO_XRCE_AGENT_BIN" udp4 -p 8888

start_bg "PX4 UAV 1" "$LOG_ROOT/px4_uav1.log" \
  env PX4_SYS_AUTOSTART="$PX4_AUTOSTART" PX4_SIM_MODEL=gz_x500 "$PX4_BIN" "$PX4_DATA_PATH" -i 1 -w "$PX4_ROOTFS_BASE/1"

sleep 8

start_bg "PX4 UAV 2" "$LOG_ROOT/px4_uav2.log" \
  env PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART="$PX4_AUTOSTART" PX4_GZ_MODEL_POSE="$UAV2_MODEL_POSE" PX4_SIM_MODEL=gz_x500 "$PX4_BIN" "$PX4_DATA_PATH" -i 2 -w "$PX4_ROOTFS_BASE/2"

echo "Waiting for PX4 topics..."
wait_for_topic "/px4_1/fmu/out/vehicle_status" "$WAIT_FOR_TOPICS_SEC"
wait_for_topic "/px4_2/fmu/out/vehicle_status" "$WAIT_FOR_TOPICS_SEC"

start_bg "uav_manager 1" "$LOG_ROOT/uav_manager_1.log" \
  ros2 run robot_control uav_manager --ros-args -p drone_id:=1

start_bg "uav_manager 2" "$LOG_ROOT/uav_manager_2.log" \
  ros2 run robot_control uav_manager --ros-args -p drone_id:=2

start_bg "mission_control_node" "$LOG_ROOT/mission_control.log" \
  ros2 run robot_control mission_control_node --ros-args -p flight_altitude_m:="$FLIGHT_ALTITUDE_M"

echo "Waiting ${WAIT_BEFORE_READY_SEC}s for estimator convergence before declaring stack ready..."
sleep "$WAIT_BEFORE_READY_SEC"

echo "Robot stack is up. No task commands have been published."
echo "Start the orchestrator ROS bridge in another terminal, then publish /orchestrator/mission_input."
echo "Press Ctrl-C to stop all managed processes."

while true; do
  sleep 5
done
