# Sutradhara-Orchestrator

This workspace contains the new `robot_control` package which has a split robot-specific `manager` that runs onboard the robot and the `mission-control` subsystem which runs off-board and interfaces with the `AI-Agent-Orch`

Current architecture note:
- `robot_control` and `robot_control_interfaces` are ROS packages built with `colcon`
- `sutradhara_orchestrator` is still a Python package managed with `uv`
- a thin ROS bridge now wraps the orchestrator so it can talk to the ROS graph

## Runtime Path Contract

Runtime paths for PX4, the underlay, and the XRCE agent are configured with environment variables or launch arguments instead of hardcoded home-directory paths.

Primary variables:
- `ROS2_WS_AI_ROOT`
- `UNDERLAY_INSTALL`
- `PX4_DIR`
- `PX4_BIN`
- `PX4_GZ_MODELS_PATH`
- `PX4_GZ_WORLDS_PATH`
- `XRCE_INSTALL`
- `MICRO_XRCE_AGENT_BIN`
- `MICRO_XRCE_AGENT_LIB_DIR`

Container-friendly defaults are used when these are unset. On a local machine, export the values that match your setup before running launch files or helper scripts.

Example local setup:

```bash
export ROS2_WS_AI_ROOT="$HOME/Projects/ros2_ws_ai"
export UNDERLAY_INSTALL="$HOME/Projects/ros2_ws/install"
export PX4_DIR="$HOME/Projects/PX4-Autopilot"
export PX4_BIN="$PX4_DIR/build/px4_sitl_default/bin/px4"
export XRCE_INSTALL="$HOME/Projects/px4_ros_uxrce_dds_ws/install"
export MICRO_XRCE_AGENT_BIN="$XRCE_INSTALL/microxrcedds_agent/bin/MicroXRCEAgent"
export MICRO_XRCE_AGENT_LIB_DIR="$XRCE_INSTALL/microxrcedds_agent/lib"
```

## Docker Boundary

The repo now includes a first-pass Docker layout around the runtime path contract:

- `Dockerfile.dev`
  - shared image for development and simulation entrypoints
- `docker-compose.yml`
  - `dev` service for build/tests/orchestrator work
  - `sim` service for Gazebo/PX4 demo runs
- `.env.docker.example`
  - host-side bind mount variables
- `scripts/docker/`
  - helper scripts for image builds, a dev shell, tests, and the sim demo

Container-internal paths are fixed and match the runtime env contract:

- repo: `/workspace/ros2_ws_ai`
- PX4 repo: `/workspace/PX4-Autopilot`
- underlay install: `/workspace/underlay/install`
- XRCE install: `/workspace/px4_ros_uxrce_dds_ws/install`

Host-side mount sources are configured separately through:

- `HOST_ROS2_WS_AI_ROOT`
- `HOST_PX4_DIR`
- `HOST_UNDERLAY_WS`
- `HOST_UNDERLAY_INSTALL`
- `HOST_XRCE_INSTALL`

If the underlay was built with `colcon --symlink-install`, its package setup hooks may point back into the original host workspace with absolute paths. For that case the Compose file also supports:

- `CONTAINER_UNDERLAY_WS`

This should be set to the same absolute path that was embedded in the host underlay when it was built. On your current machine that path is `/home/shravan/Projects/ros2_ws`.

Typical Docker workflow:

```bash
cp .env.docker.example .env
docker compose build dev sim
docker compose run --rm dev bash
```

Simulation workflow:

```bash
bash scripts/docker/run_sim_demo.sh
```

Notes:
- `dev` is the default day-to-day environment.
- `sim` mounts `/tmp/.X11-unix`; `scripts/docker/run_sim_demo.sh` also forwards `DISPLAY` and `XAUTHORITY` when available so Gazebo can open its GUI.
- the Docker boundary is defined now, but the full Gazebo/PX4 runtime inside the container still needs live validation on your teammate's machine.

## Scope

This workspace is currently validated for:
- Ubuntu 24.04 (Noble)
- ROS 2 Jazzy
- Gazebo Harmonic
- PX4 SITL with `gz_x500`
- `robot_control_interfaces` custom message package
- Micro XRCE-DDS bridge
- `robot_control` nodes: `uav_manager` and `mission_control_node`

## Important underlay requirement

`robot_control` currently depends on `px4_msgs` from an underlay workspace exposed through `UNDERLAY_INSTALL`.

That means you must source the original workspace as an underlay before building or running anything from `ros2_ws_ai`.

Build/run order for this workspace is:

```bash
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
source "$ROS2_WS_AI_ROOT/install/setup.bash"
```

If you skip the `ros2_ws` underlay, `robot_control` will not resolve `px4_msgs`.

## Build model

This workspace currently uses two build systems:

- `colcon` builds the ROS packages:
  - `robot_control`
  - `robot_control_interfaces`
- `uv` manages the Python environment for:
  - `sutradhara_orchestrator`

That is why both of these are true at the same time:
- you must `colcon build` the ROS workspace so the ROS messages/nodes exist
- you must run the orchestrator through `uv run ...` so its Python dependencies are available

This is temporary. The long-term plan is to convert the orchestrator into a fully ROS-native package/runtime.

## Install prerequisites

ROS 2 Jazzy setup is documented in:
- `/home/shravan/Projects/ros2_ws/ros2_jazzy_setup.txt`

PX4 + Harmonic + XRCE setup is documented in:
- `/home/shravan/Projects/ros2_ws/px4_harmonic_dependencies.txt`

Run them if this machine is not already prepared:

```bash
bash /home/shravan/Projects/ros2_ws/ros2_jazzy_setup.txt
bash /home/shravan/Projects/ros2_ws/px4_harmonic_dependencies.txt
```

## Build `ros2_ws_ai`

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
colcon build --symlink-install
```

Verify the package is visible:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 pkg executables robot_control
```

Expected executables:

```bash
robot_control uav_manager
robot_control mission_control_node
```

Verify the interface package is visible:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 interface package robot_control_interfaces
```

## TODO

- Convert `sutradhara_orchestrator` from a `uv`-managed Python package with a ROS bridge into a first-class ROS package/runtime
- Replace the current mixed `uv` + `colcon` startup flow with a unified ROS-native launch path
- Add real robot feedback topics for:
  - `TaskAck`
  - `TaskUpdate`
  - later richer mission state feedback

## Orchestrator interface

`mission_control_node` now subscribes to:

```bash
/orchestrator/task_command
```

Message type:

```bash
robot_control_interfaces/msg/TaskCommand
```

The orchestrator ROS bridge currently uses these ROS topics:

- `/orchestrator/mission_input`
  - type: `std_msgs/msg/String`
  - purpose: mission text into the orchestrator
- `/orchestrator/task_command`
  - type: `robot_control_interfaces/msg/TaskCommand`
  - purpose: orchestrator output to mission control
- `/orchestrator/capability_profile`
  - type: `robot_control_interfaces/msg/CapabilityProfile`
  - purpose: robot capability advertisements into the orchestrator
- `/orchestrator/robot_state`
  - type: `robot_control_interfaces/msg/RobotState`
  - purpose: robot heartbeat/state into the orchestrator
- `/orchestrator/mission_result`
  - type: `std_msgs/msg/String`
  - purpose: JSON-encoded mission summary/status out of the orchestrator

Current implementation behavior:
- supports `ASSIGN`
- routes by `robot_id`
- supports `POINT` and `REGION` targets
- translates the target points into the existing `PoseArray` mission input for `uav_manager`
- ignores unsupported command types for now

Current non-goals for this step:
- idempotency
- `CANCEL`, `PAUSE`, `RESUME`, `UPDATE_PRIORITY` execution
- `ASSET_ID` target handling

## Running the orchestrator ROS bridge

The orchestrator is not a ROS package yet. It runs as a Python package, but once started it behaves like a ROS node through the bridge wrapper.

Run it with:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
cd src/sutradhara_orchestrator
uv run python -m sutradhara_orchestrator.cli ros-bridge
```

Send a mission into it with:

```bash
ros2 topic pub --once /orchestrator/mission_input std_msgs/msg/String "{data: 'Inspect the area around the two drones and report anomalies'}"
```

What the bridge does:
- receives mission text on ROS
- feeds it into `AgenticAI`
- receives internal broker `task_command` events
- republishes them as ROS `TaskCommand`
- receives ROS `CapabilityProfile` and `RobotState`
- feeds them into the orchestrator world-state manager

## Automated two-UAV test

You can run the full integration test with one command:

```bash
cd /home/shravan/Projects/ros2_ws_ai
bash scripts/test_two_uav_mission.sh
```

The script:
- starts `MicroXRCEAgent`
- starts PX4 SITL instance `1`
- starts PX4 SITL instance `2`
- starts `uav_manager` for `drone_id:=1`
- starts `uav_manager` for `drone_id:=2`
- starts `mission_control_node`
- publishes one `TaskCommand` for each UAV

Logs are written under:

```bash
/home/shravan/Projects/ros2_ws_ai/test_logs/<timestamp>/
```

Useful environment overrides:

```bash
WAIT_BEFORE_COMMANDS_SEC=30 bash scripts/test_two_uav_mission.sh
UAV2_MODEL_POSE="0,5" bash scripts/test_two_uav_mission.sh
FLIGHT_ALTITUDE_M=10.0 bash scripts/test_two_uav_mission.sh
```

The script assumes:
- the workspace is already built
- the PX4 SITL binary already exists at `/home/shravan/Projects/PX4-Autopilot/build/px4_sitl_default/bin/px4`
- no other `MicroXRCEAgent` or PX4 instance `1` / `2` is already running

This script currently exercises the ROS robot-control path only.
It does not start the orchestrator ROS bridge.

## Bring-up only script

If you want the robot stack up without auto-publishing any commands, use:

```bash
cd /home/shravan/Projects/ros2_ws_ai
bash scripts/bringup_two_uav_stack.sh
```

This script starts only:
- `MicroXRCEAgent`
- PX4 SITL instance `1`
- PX4 SITL instance `2`
- `uav_manager` for `drone_id:=1`
- `uav_manager` for `drone_id:=2`
- `mission_control_node`

It does not publish any `TaskCommand`.

This is the recommended script when testing the orchestrator ROS bridge.

## Runtime bring-up

Use three terminals.

### Terminal A: Micro XRCE-DDS Agent

```bash
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/px4_ros_uxrce_dds_ws/install/setup.bash
MicroXRCEAgent udp4 -p 8888
```

### Terminal B: PX4 SITL + Gazebo Harmonic

```bash
cd /home/shravan/Projects/PX4-Autopilot
make px4_sitl gz_x500
```

Wait until PX4 startup finishes and the vehicle is ready.

### Terminal C: `uav_manager`

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 run robot_control uav_manager --ros-args \
  -r /px4_0/fmu/in/offboard_control_mode:=/fmu/in/offboard_control_mode \
  -r /px4_0/fmu/in/trajectory_setpoint:=/fmu/in/trajectory_setpoint \
  -r /px4_0/fmu/in/vehicle_command:=/fmu/in/vehicle_command \
  -r /px4_0/fmu/out/vehicle_status:=/fmu/out/vehicle_status \
  -r /px4_0/fmu/out/vehicle_local_position:=/fmu/out/vehicle_local_position
```

To test the orchestrator against the real robot stack, you still need the whole robot-control runtime up:

- `MicroXRCEAgent`
- PX4 SITL / Gazebo
- `uav_manager` instances
- `mission_control_node`
- the orchestrator ROS bridge

The C++/Python split is not a problem by itself. ROS messages are the contract between them, so as long as both sides agree on the interface package and the topics are sourced correctly, C++ nodes and Python nodes interoperate normally.

## Why the remaps are required

Current `uav_manager` still builds PX4-facing topic names under:

- `/px4_0/fmu/in/...`
- `/px4_0/fmu/out/...`

But in the working SITL setup, the actual PX4 bridge topics are:

- `/fmu/in/...`
- `/fmu/out/...`

Without the remaps above, `uav_manager` will change state internally but PX4 will not receive the commands.

## Confirm the PX4 bridge is alive

Run this in a separate terminal after PX4 and XRCE agent are up:

```bash
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
ros2 topic list | grep '^/fmu/'
```

You should see topics such as:

```bash
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
/fmu/out/vehicle_local_position
/fmu/out/vehicle_status
```

## Start a mission

You have two options.

### Option A: publish a trajectory manually

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 topic pub --once /px4_0/trajectory_upload geometry_msgs/msg/PoseArray "{
  header: {frame_id: 'map'},
  poses: [
    {position: {x: 0.0, y: 0.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 0.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 5.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 0.0, y: 5.0, z: -8.0}, orientation: {w: 1.0}}
  ]
}"
```

Notes:
- PX4 local NED uses negative `z` for altitude above home.
- `z: -8.0` means approximately 8 meters above takeoff height.

### Option B: use `mission_control_node`

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 run robot_control mission_control_node
```

Important:
- `mission_control_node` no longer publishes a hardcoded mission on startup
- it waits for `TaskCommand` messages on `/orchestrator/task_command`
- it uses `robot_id` from the command to select the target robot namespace

Example command for a single UAV:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 topic pub --once /orchestrator/task_command robot_control_interfaces/msg/TaskCommand "{
  mission_id: 'mission_001',
  task_id: 'task_001',
  command_id: 'cmd_001',
  robot_id: 'px4_0',
  type: 0,
  priority: 50,
  task: {
    task_type: 0,
    target: {
      frame: 'map',
      kind: 1,
      points: [
        {x: 0.0, y: 0.0},
        {x: 5.0, y: 0.0},
        {x: 5.0, y: 5.0},
        {x: 0.0, y: 5.0}
      ],
      asset_id: ''
    },
    constraints: {
      safety_radius_m: 0.0,
      min_battery_pct_to_start: 0.0,
      require_sensors: []
    },
    success_criteria: {
      criteria: ['ASSET_VISITED']
    }
  }
}"
```

Enum values used above:
- `type: 0` means `ASSIGN`
- `task_type: 0` means `INSPECT`
- `target.kind: 1` means `REGION`

## What each node does

`uav_manager`:
- subscribes to `/px4_0/trajectory_upload`
- publishes offboard control mode
- publishes trajectory setpoints
- publishes arm/mode vehicle commands
- subscribes to local position and vehicle status
- runs the flight state machine:
  `WAITING -> TAKING_OFF -> HOVERING -> FOLLOWING_TRAJECTORY`

`mission_control_node`:
- subscribes to `/orchestrator/task_command`
- parses the structured orchestrator command
- routes by `robot_id`
- translates supported commands into `geometry_msgs/msg/PoseArray`
- publishes to `/<robot_id>/trajectory_upload`

## Full command sequence that should fly the drone

Terminal A:

```bash
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/px4_ros_uxrce_dds_ws/install/setup.bash
MicroXRCEAgent udp4 -p 8888
```

Terminal B:

```bash
cd /home/shravan/Projects/PX4-Autopilot
make px4_sitl gz_x500
```

Terminal C:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 run robot_control uav_manager --ros-args \
  -r /px4_0/fmu/in/offboard_control_mode:=/fmu/in/offboard_control_mode \
  -r /px4_0/fmu/in/trajectory_setpoint:=/fmu/in/trajectory_setpoint \
  -r /px4_0/fmu/in/vehicle_command:=/fmu/in/vehicle_command \
  -r /px4_0/fmu/out/vehicle_status:=/fmu/out/vehicle_status \
  -r /px4_0/fmu/out/vehicle_local_position:=/fmu/out/vehicle_local_position
```

Terminal D:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 run robot_control mission_control_node
```

Terminal E:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 topic pub --once /orchestrator/task_command robot_control_interfaces/msg/TaskCommand "{
  mission_id: 'mission_001',
  task_id: 'task_001',
  command_id: 'cmd_001',
  robot_id: 'px4_0',
  type: 0,
  priority: 50,
  task: {
    task_type: 0,
    target: {
      frame: 'map',
      kind: 1,
      points: [
        {x: 0.0, y: 0.0},
        {x: 5.0, y: 0.0},
        {x: 5.0, y: 5.0},
        {x: 0.0, y: 5.0}
      ],
      asset_id: ''
    },
    constraints: {
      safety_radius_m: 0.0,
      min_battery_pct_to_start: 0.0,
      require_sensors: []
    },
    success_criteria: {
      criteria: ['ASSET_VISITED']
    }
  }
}"
```

## Two-UAV setup without code changes

Yes. The current system can fly two PX4 SITL drones without changing the code.

The important trick is:
- do not use PX4 instance `0`
- start the two vehicles as PX4 instances `1` and `2`

Why this works:
- PX4 automatically gives ROS 2 namespaces to instances greater than zero
- instance `1` gets `/px4_1/...`
- instance `2` gets `/px4_2/...`
- `uav_manager` already expects `/px4_<id>/fmu/...`

This avoids the single-vehicle mismatch where instance `0` publishes on `/fmu/...`.

PX4 documents that instances greater than zero get a namespace `px4_$px4_instance`, and that starting from index `1` avoids the first-instance mismatch:
- https://docs.px4.io/main/en/ros2/multi_vehicle
- https://docs.px4.io/main/en/middleware/uxrce_dds

### Two-UAV bring-up

Use five terminals.

### Terminal A: Micro XRCE-DDS Agent

```bash
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/px4_ros_uxrce_dds_ws/install/setup.bash
MicroXRCEAgent udp4 -p 8888
```

### Terminal B: PX4 UAV 1

```bash
cd /home/shravan/Projects/PX4-Autopilot
make px4_sitl
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500 ./build/px4_sitl_default/bin/px4 -i 1
```

### Terminal C: PX4 UAV 2

```bash
cd /home/shravan/Projects/PX4-Autopilot
PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL_POSE="0,1" PX4_SIM_MODEL=gz_x500 ./build/px4_sitl_default/bin/px4 -i 2
```

Notes:
- Terminal B starts Gazebo and the first vehicle.
- Terminal C connects the second PX4 instance to the already-running Gazebo server.
- `PX4_GZ_MODEL_POSE="0,1"` offsets the second drone so both vehicles do not spawn at the same position.

### Terminal D: `uav_manager` for UAV 1

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 run robot_control uav_manager --ros-args -p drone_id:=1
```

### Terminal E: `uav_manager` for UAV 2

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 run robot_control uav_manager --ros-args -p drone_id:=2
```

No remaps are needed in this two-UAV setup because the PX4 namespaces already match the manager topic convention.

### Trigger both UAVs with `mission_control_node`

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 run robot_control mission_control_node --ros-args -p drone_ids:="['/px4_1','/px4_2']"
```

This command is now outdated for the current implementation.

For two UAVs, run `mission_control_node` once:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 run robot_control mission_control_node
```

Then publish one `TaskCommand` per robot:
- `robot_id: 'px4_1'`
- `robot_id: 'px4_2'`

### Manual per-UAV mission upload

You can also command each vehicle separately.

UAV 1:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 topic pub --once /px4_1/trajectory_upload geometry_msgs/msg/PoseArray "{
  header: {frame_id: 'map'},
  poses: [
    {position: {x: 0.0, y: 0.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 0.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 5.0, z: -8.0}, orientation: {w: 1.0}}
  ]
}"
```

UAV 2:

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash

ros2 topic pub --once /px4_2/trajectory_upload geometry_msgs/msg/PoseArray "{
  header: {frame_id: 'map'},
  poses: [
    {position: {x: 0.0, y: 1.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 1.0, z: -8.0}, orientation: {w: 1.0}},
    {position: {x: 5.0, y: 6.0, z: -8.0}, orientation: {w: 1.0}}
  ]
}"
```

### Verify both PX4 bridges are present

```bash
cd /home/shravan/Projects/ros2_ws_ai
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
ros2 topic list | grep '^/px4_[12]/fmu/'
```

You should see topics for both:
- `/px4_1/fmu/in/...`
- `/px4_1/fmu/out/...`
- `/px4_2/fmu/in/...`
- `/px4_2/fmu/out/...`

## Troubleshooting

- `robot_control` build fails with missing `px4_msgs`:
  You did not source `/home/shravan/Projects/ros2_ws/install/setup.bash` before building or running.

- `uav_manager` changes state but vehicle does not move:
  The FMU namespace remaps were not applied. Use the exact remap command shown above.

- `gz-harmonic` cannot be installed:
  Re-run `/home/shravan/Projects/ros2_ws/px4_harmonic_dependencies.txt`.

- PX4 setup hits `externally-managed-environment`:
  The dependency script already handles this with `PIP_BREAK_SYSTEM_PACKAGES=1`.

- `px4_msgs` or `px4_ros_com` fail with symlink-install errors:
  This is usually caused by stale in-source build artifacts. The dependency script now cleans them.

- `mission_control_node` does not trigger the UAV:
  Make sure `uav_manager` is already running and you published a `TaskCommand` to `/orchestrator/task_command` with the correct `robot_id`.

## Standalone later

If you want `ros2_ws_ai` to become fully standalone later, move or duplicate the required PX4 interface dependencies into this workspace, starting with:

- `px4_msgs`
- any future shared PX4 bridge packages or custom interfaces
