#!/usr/bin/env bash
# Launches the full sim stack inside a VNC-enabled container.
# Open http://localhost:6080/vnc.html in any browser to view Gazebo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

docker compose run --rm -p 6080:6080 sim-vnc bash -lc "
  Xvfb :99 -screen 0 1920x1080x24 &
  x11vnc -display :99 -forever -nopw -quiet &
  websockify --web /usr/share/novnc 6080 localhost:5900 &
  echo 'noVNC ready at http://localhost:6080/vnc.html'
  cd \"\$ROS2_WS_AI_ROOT\" &&
  ros2 launch inspection_sim inspection_multi_robot_demo.launch.py headless:=false
"
