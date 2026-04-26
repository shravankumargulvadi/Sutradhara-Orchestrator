# Sutradhara-Orchestrator

This repository contains the inspection demo stack for:

- the simulation world in `inspection_sim`
- the ROS execution nodes in `robot_control` and `robot_control_interfaces`
- the Python orchestrator in `src/sutradhara_orchestrator`

The current end-to-end path is:

1. mission text enters the orchestrator on `/orchestrator/mission_input`
2. the orchestrator emits `TaskCommand`
3. `mission_control_node` resolves routes and publishes `PoseArray`
4. `uav_manager` drives PX4 offboard control
5. task feedback and anomaly summaries return on `/orchestrator/task_ack` and `/orchestrator/task_update`

For simulation details, world layout, sectors, and route data, see [src/inspection_sim/README.md](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/README.md).

## Workspace Layout

- `src/inspection_sim`
  - Gazebo world, reusable models, and semantic config (`assets.yaml`, `sectors.yaml`, `routes.yaml`)
- `src/robot_control_interfaces`
  - custom ROS messages
- `src/robot_control`
  - `uav_manager` and `mission_control_node`
- `src/sutradhara_orchestrator`
  - Python orchestrator, planner, bridge, and tests
- `docker/`
  - pinned external dependency manifest and Docker entrypoint
- `scripts/docker/`
  - helper scripts for the Docker workflow

## Runtime Path Contract

The stack resolves external runtime locations through environment variables or launch arguments.

Primary variables:

- `ROS2_WS_AI_ROOT`
- `UNDERLAY_INSTALL`
- `PX4_DIR`
- `PX4_BIN`
- `PX4_ROOTFS_BASE`
- `PX4_GZ_MODELS_PATH`
- `PX4_GZ_WORLDS_PATH`
- `XRCE_INSTALL`
- `MICRO_XRCE_AGENT_BIN`
- `MICRO_XRCE_AGENT_LIB_DIR`

Current defaults:

- Docker/self-contained image:
  - `PX4_DIR=/opt/px4`
  - `UNDERLAY_INSTALL=/opt/underlay_ws/install`
  - `XRCE_INSTALL=/opt/xrce_ws/install`
- local non-Docker workflow:
  - export the values that match your local host setup before running launch files or helper scripts

## Frozen External Sources

The pinned external dependency set is recorded in [docker/dependencies.repos](/home/shravan/Projects/ros2_ws_ai/docker/dependencies.repos).

It currently includes:

- `PX4-Autopilot`
- `px4_msgs`
- `Micro-XRCE-DDS-Agent`

`px4_ros_com` is intentionally excluded. The current stack builds directly against `px4_msgs`, and the PX4 <-> ROS 2 path is:

- PX4 uXRCE client
- Micro XRCE-DDS Agent
- `px4_msgs`

## Docker Workflow

Docker is now the recommended workflow.

The image architecture is:

- `base`
  - ROS Jazzy, Gazebo Harmonic, build tools
- `deps-src`
  - imports pinned external repos from `docker/dependencies.repos`
- `deps`
  - builds PX4, `px4_msgs`, and `microxrcedds_agent`
- `workspace`
  - builds the ROS workspace and installs the Python orchestrator
- `runtime`
  - final runnable image

Compose services:

- `dev`
  - bind-mounts this repo for active development
- `sim`
  - runs the baked PX4/XRCE/underlay image for the simulation demo

### Build the images

```bash
cd /home/shravan/Projects/ros2_ws_ai
cp .env.docker.example .env
docker compose build dev sim
```

### Open a development shell

```bash
cd /home/shravan/Projects/ros2_ws_ai
docker compose run --rm dev bash
```

Inside `dev`, rebuild the workspace after source changes:

```bash
cd $ROS2_WS_AI_ROOT
colcon build --symlink-install
source /opt/ros/jazzy/setup.bash
source $UNDERLAY_INSTALL/setup.bash
source install/setup.bash
```

### Run the simulation stack

Recommended:

```bash
cd /home/shravan/Projects/ros2_ws_ai
bash scripts/docker/run_sim_demo.sh
```

This launches the `sim` service and:

- starts Gazebo
- starts `MicroXRCEAgent`
- starts PX4 SITL
- starts `uav_manager`
- starts `mission_control_node`
- starts the ground rover ROS-Gazebo bridge

If `DISPLAY` and `XAUTHORITY` are available, the script launches Gazebo with GUI support. Otherwise it falls back to headless mode.

### Run the ROS bridge

In a second terminal:

```bash
cd /home/shravan/Projects/ros2_ws_ai
docker compose run --rm dev bash -lc '
  cd $ROS2_WS_AI_ROOT/src/sutradhara_orchestrator &&
  python3 -m sutradhara_orchestrator.cli ros-bridge
'
```

Wait until you see:

```text
ROS bridge ready. Listening on /orchestrator/mission_input
```

### Publish a mission

In a third terminal:

```bash
cd /home/shravan/Projects/ros2_ws_ai
docker compose run --rm dev bash -lc '
  source /opt/ros/jazzy/setup.bash &&
  source $UNDERLAY_INSTALL/setup.bash &&
  source $ROS2_WS_AI_ROOT/install/setup.bash &&
  ros2 topic pub /orchestrator/mission_input std_msgs/msg/String "{data: '\''Patrol sector 1'\''}" -r 1 -t 5
'
```

The repeated publish is deliberate. Across short-lived containers, it is more reliable than a single `--once` sample.

### Useful Docker helper scripts

- [scripts/docker/build_images.sh](/home/shravan/Projects/ros2_ws_ai/scripts/docker/build_images.sh)
- [scripts/docker/dev_shell.sh](/home/shravan/Projects/ros2_ws_ai/scripts/docker/dev_shell.sh)
- [scripts/docker/run_tests.sh](/home/shravan/Projects/ros2_ws_ai/scripts/docker/run_tests.sh)
- [scripts/docker/run_sim_demo.sh](/home/shravan/Projects/ros2_ws_ai/scripts/docker/run_sim_demo.sh)

## Local Non-Docker Workflow

The older local-host workflow still works, but it is now the secondary path.

Set the runtime paths to match your machine:

```bash
export ROS2_WS_AI_ROOT="$HOME/Projects/ros2_ws_ai"
export UNDERLAY_INSTALL="$HOME/Projects/ros2_ws/install"
export PX4_DIR="$HOME/Projects/PX4-Autopilot"
export PX4_BIN="$PX4_DIR/build/px4_sitl_default/bin/px4"
export PX4_ROOTFS_BASE="$PX4_DIR/build/px4_sitl_default/rootfs"
export XRCE_INSTALL="$HOME/Projects/px4_ros_uxrce_dds_ws/install"
export MICRO_XRCE_AGENT_BIN="$XRCE_INSTALL/microxrcedds_agent/bin/MicroXRCEAgent"
export MICRO_XRCE_AGENT_LIB_DIR="$XRCE_INSTALL/microxrcedds_agent/lib"
```

Build:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
colcon build --symlink-install
```

Run the one-UAV demo:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
source "$ROS2_WS_AI_ROOT/install/setup.bash"
ros2 launch inspection_sim inspection_uav_demo.launch.py
```

Run the ROS bridge locally:

```bash
cd "$ROS2_WS_AI_ROOT/src/sutradhara_orchestrator"
uv run python -m sutradhara_orchestrator.cli ros-bridge
```

## ROS Interface

Main orchestrator-facing topics:

- `/orchestrator/mission_input`
  - `std_msgs/msg/String`
- `/orchestrator/task_command`
  - `robot_control_interfaces/msg/TaskCommand`
- `/orchestrator/capability_profile`
  - `robot_control_interfaces/msg/CapabilityProfile`
- `/orchestrator/robot_state`
  - `robot_control_interfaces/msg/RobotState`
- `/orchestrator/task_ack`
  - `robot_control_interfaces/msg/TaskAck`
- `/orchestrator/task_update`
  - `robot_control_interfaces/msg/TaskUpdate`
- `/orchestrator/mission_result`
  - `std_msgs/msg/String`

Current patrol convention:

- `task.task_type = PATROL`
- `task.target.kind = SECTOR_ID`
- `task.target.sector_id = <sector_id>`

`mission_control_node` resolves sector patrols through the data in:

- [src/inspection_sim/config/sectors.yaml](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/sectors.yaml)
- [src/inspection_sim/config/routes.yaml](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml)

## Two-UAV Scripts

The repo still includes the older helper scripts for two-UAV bring-up:

- [scripts/bringup_two_uav_stack.sh](/home/shravan/Projects/ros2_ws_ai/scripts/bringup_two_uav_stack.sh)
- [scripts/test_two_uav_mission.sh](/home/shravan/Projects/ros2_ws_ai/scripts/test_two_uav_mission.sh)

They now assume the same runtime path contract as the rest of the stack:

- `PX4_DIR`
- `PX4_BIN`
- `PX4_ROOTFS_BASE`
- `UNDERLAY_INSTALL`
- `XRCE_INSTALL`

Those scripts are still useful for host-side experimentation, but the primary documented flow is now:

- `run_sim_demo.sh`
- ROS bridge
- mission publish

## Build Model

This repository still uses two build systems:

- `colcon`
  - ROS packages
- `uv`
  - local Python development workflow for the orchestrator

In Docker, the runtime image already installs the Python orchestrator package, so `python3 -m sutradhara_orchestrator.cli ros-bridge` works directly.

For local non-Docker development, `uv run ...` remains the intended Python workflow.

## Troubleshooting

- `inspection_sim` is missing after `docker compose down -v`:
  Recreate the `dev` container and rebuild the workspace before launching anything:
  `docker compose run --rm dev bash -lc 'cd $ROS2_WS_AI_ROOT && colcon build --symlink-install'`

- Mission input is not received by the bridge:
  Start the bridge first, then publish with `-r 1 -t 5` instead of `--once`.

- Gazebo GUI does not open in Docker:
  Make sure the host has valid `DISPLAY` and `XAUTHORITY` and launch via `bash scripts/docker/run_sim_demo.sh`.

- Gazebo GUI is very laggy in Docker:
  This is usually X11/container rendering overhead or incomplete GPU acceleration inside the container.

- `robot_control` build fails locally with missing `px4_msgs`:
  You did not source the local underlay before building or running.

- Docker commands suddenly require `sudo` again:
  The Docker socket permissions on your host were reset. This is a host Docker configuration issue, not a repo issue.

## Current Scope

Validated target stack:

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- PX4 SITL with `gz_x500`
- `robot_control_interfaces`
- `robot_control`
- `inspection_sim`
- `sutradhara_orchestrator` via ROS bridge

## Next Major Direction

The current architecture is still a staged MVP:

- sectors and routes are data-driven
- patrol execution is real
- anomaly reporting is config-driven
- the orchestrator can issue sector patrols

The next major step is to make the image fully validated end to end and then publish it for teammate use without host dependency setup.
