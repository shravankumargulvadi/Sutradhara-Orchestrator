#!/usr/bin/env bash

set -eo pipefail

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

if [[ -n "${UNDERLAY_INSTALL:-}" && -f "${UNDERLAY_INSTALL}/setup.bash" ]]; then
  # shellcheck disable=SC1090
  source "${UNDERLAY_INSTALL}/setup.bash"
fi

if [[ "${AUTO_SOURCE_WORKSPACE_INSTALL:-1}" == "1" && -n "${ROS2_WS_AI_ROOT:-}" && -f "${ROS2_WS_AI_ROOT}/install/setup.bash" ]]; then
  # shellcheck disable=SC1090
  source "${ROS2_WS_AI_ROOT}/install/setup.bash"
fi

exec "$@"
