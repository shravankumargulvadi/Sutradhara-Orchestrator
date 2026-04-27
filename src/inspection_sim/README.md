# inspection_sim

`inspection_sim` is the simulation-assets package for infrastructure inspection demos in this workspace.

It currently provides a primitive-based solar farm world for Gazebo Harmonic, along with reusable SDF models, asset metadata, route definitions, and a launch entrypoint.

## Purpose

This package exists to make the demo environment a first-class part of the repository instead of relying on PX4's default empty world.

The current solar farm is designed to support:

- a recognizable outdoor inspection environment
- stable named infrastructure assets
- repeatable preplanned UAV inspection routes
- future extension to dynamic autonomy and ground robot integration

## Package Layout

The package is intentionally split into four layers:

- `worlds/`
  - top-level Gazebo world composition
- `models/`
  - reusable SDF models referenced by the world
- `config/`
  - semantic inspection data such as asset IDs, sector definitions, and route definitions
- `launch/`
  - ROS launch entrypoint for running the world

Generated files:

- [`CMakeLists.txt`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/CMakeLists.txt)
- [`package.xml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/package.xml)
- [`README.md`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/README.md)
- [`worlds/solar_farm_world.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/worlds/solar_farm_world.sdf)
- [`models/solar_panel_row/model.config`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/solar_panel_row/model.config)
- [`models/solar_panel_row/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/solar_panel_row/model.sdf)
- [`models/inverter_pad/model.config`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/inverter_pad/model.config)
- [`models/inverter_pad/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/inverter_pad/model.sdf)
- [`models/battery_container/model.config`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/battery_container/model.config)
- [`models/battery_container/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/battery_container/model.sdf)
- [`models/fence_segment/model.config`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/fence_segment/model.config)
- [`models/fence_segment/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/fence_segment/model.sdf)
- [`models/weather_station/model.config`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/weather_station/model.config)
- [`models/weather_station/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/weather_station/model.sdf)
- [`config/assets.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/assets.yaml)
- [`config/sectors.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/sectors.yaml)
- [`config/routes.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml)
- [`launch/solar_farm_world.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/solar_farm_world.launch.py)
- [`launch/inspection_uav_demo.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/inspection_uav_demo.launch.py)

## How The World Was Created

The solar farm was built with simple SDF primitives instead of downloaded meshes. That was the fastest way to get a versioned, maintainable, and performant environment into the repo.

The top-level world file is [`worlds/solar_farm_world.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/worlds/solar_farm_world.sdf).

It does three jobs:

1. Defines the global Gazebo scene.
   - physics system plugins
   - directional lighting
   - background and camera
   - ground plane

2. Creates site-wide geometry directly in the world file.
   - service roads
   - maintenance laydown pad
   - anomaly marker

3. Composes the solar farm using reusable `model://` includes.
   - 16 panel rows
   - 2 inverter pads
   - 1 battery container
   - fence segments
   - 1 weather station

This keeps the world file focused on placement and site composition, while the actual reusable geometry lives in `models/`.

## Reusable Models

Each model lives in its own directory under `models/` and contains:

- `model.config`
- `model.sdf`

These are the current models:

- [`models/solar_panel_row/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/solar_panel_row/model.sdf)
  - one repeated solar panel table with a tilted panel surface, frame beams, and support posts
- [`models/inverter_pad/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/inverter_pad/model.sdf)
  - a concrete electrical pad with cabinets, a transformer block, and a hotspot marker
- [`models/battery_container/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/battery_container/model.sdf)
  - a utility-scale battery container with a visible thermal alert patch
- [`models/fence_segment/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/fence_segment/model.sdf)
  - a simple perimeter fence segment with posts and a thin mesh-like panel
- [`models/weather_station/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/weather_station/model.sdf)
  - a weather mast for context and an additional inspection target

These models are deliberately simple. They are meant to read clearly from an aerial viewpoint and remain easy to adjust.

## Site Contents

The current solar farm world includes:

- 16 solar panel rows
- 2 inverter pads
- 1 battery container
- 1 weather station
- perimeter fencing
- service roads
- maintenance laydown area
- visible anomaly cues

The anomaly cues are visual only for now. They exist to make the environment feel inspectable before perception and autonomy are integrated.

## Semantic Inspection Data

Three YAML files define the inspection-facing semantic layer.

### Assets

[`config/assets.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/assets.yaml) contains stable infrastructure asset IDs and their coordinates.

Examples:

- `row_06`
- `inverter_01`
- `battery_container_01`
- `weather_station_01`
- `north_perimeter_gate`

Each asset can include:

- `type`
- `pose`
- `inspection_points`
- `notes`

This file is the source of truth for what the robot is supposed to inspect.

### Routes

[`config/routes.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml) contains named UAV routes.

Current routes:

- `perimeter_overview`
- `critical_assets_inspection`
- `patrol_sector_1`
- `patrol_sector_2`
- `patrol_sector_3`
- `patrol_sector_4`

Each route includes:

- route ID
- description
- robot type
- nominal altitude
- assets covered
- ordered waypoint list

These routes are not yet automatically consumed by the mission stack. They were added now so the environment, asset catalog, and future execution logic all share the same coordinates.

### Sectors

[`config/sectors.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/sectors.yaml) defines the planning abstraction that the orchestrator can use for MVP patrol missions.

Current sectors:

- `sector_1`
- `sector_2`
- `sector_3`
- `sector_4`

Each sector includes:

- sector ID
- display name
- default patrol route
- assets contained in that sector

For the current MVP, the intended abstraction is:

- orchestrator thinks in sectors
- mission control resolves sector to route
- `uav_manager` flies the resulting waypoints

The sector-to-route mapping is currently implemented inside `mission_control_node`.

## How Launch Works

[`launch/solar_farm_world.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/solar_farm_world.launch.py) is the ROS launch entrypoint for the world.

It does two important things:

1. Resolves the installed package share path using `ament_index_python`
2. Sets `GZ_SIM_RESOURCE_PATH` to the package's `models/` directory

That environment variable allows Gazebo to resolve the `model://solar_panel_row`, `model://inverter_pad`, and similar includes referenced by the world file.

It then launches:

```bash
gz sim -r <world file>
```

[`launch/inspection_uav_demo.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/inspection_uav_demo.launch.py) is the repo-owned end-to-end demo launcher for one UAV.

It starts the stack in this order:

1. Gazebo with the solar farm world
2. `MicroXRCEAgent`
3. the PX4 SITL binary resolved through `PX4_BIN`
4. `robot_control uav_manager`
5. `robot_control mission_control_node`

The launch file does not vendor PX4 into this package. It resolves PX4, the `px4_msgs` underlay, and the XRCE agent from the runtime environment.

[`launch/inspection_multi_robot_demo.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/inspection_multi_robot_demo.launch.py) is the repo-owned launch entrypoint for the combined UAV and ground inspection rover demo.

It starts:

- Gazebo with the solar farm world and `inspection_rover_01`
- PX4 SITL, `MicroXRCEAgent`, `uav_manager`, and `mission_control_node` for `x500_1`
- `ros_gz_bridge parameter_bridge` for the rover command and sensor topics
- `ground_robot_manager` for rover capability and state publication

The rover is a primitive differential-drive SDF model in [`models/inspection_rover/model.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models/inspection_rover/model.sdf). It is intentionally repo-local so the demo does not depend on downloaded meshes or external model servers.

Rover ROS topics exposed by the bridge:

- `/ugv_1/cmd_vel` (`geometry_msgs/msg/Twist`)
- `/ugv_1/odom` (`nav_msgs/msg/Odometry`)
- `/ugv_1/scan` (`sensor_msgs/msg/LaserScan`)
- `/ugv_1/camera/image_raw` (`sensor_msgs/msg/Image`)
- `/ugv_1/depth/image_raw` (`sensor_msgs/msg/Image`)
- `/ugv_1/imu` (`sensor_msgs/msg/Imu`)

That means the same launch file works in both modes:

- Docker/self-contained image
  - defaults resolve to `/opt/px4`, `/opt/underlay_ws/install`, and `/opt/xrce_ws/install`
- local non-Docker workflow
  - export the matching host paths first

Runtime paths are resolved from environment variables or launch arguments rather than fixed host paths.

Common variables:
- `PX4_DIR`
- `PX4_BIN`
- `PX4_GZ_MODELS_PATH`
- `PX4_GZ_WORLDS_PATH`
- `UNDERLAY_INSTALL`
- `XRCE_INSTALL`
- `MICRO_XRCE_AGENT_BIN`
- `MICRO_XRCE_AGENT_LIB_DIR`

## Build And Run

Docker is the recommended workflow now.

### Docker

Build the image and open a dev shell:

```bash
cd "$ROS2_WS_AI_ROOT"
cp .env.docker.example .env
docker compose build dev sim
docker compose run --rm dev bash
```

Inside the `dev` container:

```bash
cd "$ROS2_WS_AI_ROOT"
colcon build --symlink-install
```

Run the one-UAV demo from the host:

```bash
cd "$ROS2_WS_AI_ROOT"
bash scripts/docker/run_sim_demo.sh
```

### Local non-Docker

Build only this package:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
colcon build --packages-select inspection_sim
```

Run the world:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
source "$ROS2_WS_AI_ROOT/install/setup.bash"
ros2 launch inspection_sim solar_farm_world.launch.py
```

Run the one-UAV solar farm demo:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$UNDERLAY_INSTALL/setup.bash"
source "$ROS2_WS_AI_ROOT/install/setup.bash"
ros2 launch inspection_sim inspection_uav_demo.launch.py
```

Run the combined UAV and ground rover demo:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$ROS2_WS_AI_ROOT/install/setup.bash"
ros2 launch inspection_sim inspection_multi_robot_demo.launch.py
```

In another terminal, command the rover forward:

```bash
cd "$ROS2_WS_AI_ROOT"
source /opt/ros/jazzy/setup.bash
source "$ROS2_WS_AI_ROOT/install/setup.bash"
ros2 topic pub --once /ugv_1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.6}, angular: {z: 0.0}}"
```

Turn the rover in place:

```bash
ros2 topic pub --once /ugv_1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.6}}"
```

Confirm bridged rover topics:

```bash
ros2 topic list | grep /ugv_1
ros2 topic echo --once /ugv_1/odom
ros2 topic echo --once /ugv_1/scan
```

Confirm the rover is visible to the orchestrator-facing robot registry:

```bash
ros2 topic echo --once /orchestrator/capability_profile
ros2 topic echo --once /orchestrator/robot_state
```

Expected streams include both `px4_1` from `uav_manager` and `ugv_1` from `ground_robot_manager`.

`ground_robot_manager` also accepts orchestrator `ASSIGN` commands for `ugv_1` on `/orchestrator/task_command`. The initial implementation supports point/region waypoint lists and sector patrol tasks by resolving the configured sector route and following the route on the ground with `/ugv_1/cmd_vel`. It publishes task acceptance on `/orchestrator/task_ack` and progress/completion on `/orchestrator/task_update`.

Send a direct sector patrol task to the rover:

```bash
ros2 topic pub --once /orchestrator/task_command robot_control_interfaces/msg/TaskCommand "{
  mission_id: 'manual_ugv_patrol',
  task_id: 'ugv_patrol_sector_3',
  command_id: 'cmd_ugv_patrol_sector_3',
  robot_id: 'ugv_1',
  type: 0,
  priority: 80,
  task: {
    task_type: 3,
    target: {
      frame: 'map',
      kind: 3,
      points: [],
      asset_id: '',
      sector_id: 'sector_3'
    },
    constraints: {
      safety_radius_m: 0.0,
      min_battery_pct_to_start: 10.0,
      require_sensors: []
    },
    success_criteria: {
      criteria: ['GROUND_PATROL_COMPLETE']
    }
  }
}"
```

Watch the rover task feedback:

```bash
ros2 topic echo /orchestrator/task_ack
ros2 topic echo /orchestrator/task_update
```

Useful launch arguments:

```bash
ros2 launch inspection_sim inspection_uav_demo.launch.py flight_altitude_m:=10.0
ros2 launch inspection_sim inspection_uav_demo.launch.py gz_model_pose:="0,0,0.2,0,0,0"
ros2 launch inspection_sim inspection_uav_demo.launch.py px4_dir:="$PX4_DIR"
ros2 launch inspection_sim inspection_multi_robot_demo.launch.py headless:=false
```

## End-To-End Patrol Demo

To validate the full mission-text-driven patrol flow, use three terminals.

Docker is the primary documented path.

### Terminal 1

Start the simulation stack:

```bash
cd "$ROS2_WS_AI_ROOT"
bash scripts/docker/run_sim_demo.sh
```

### Terminal 2

Start the orchestrator ROS bridge:

```bash
cd "$ROS2_WS_AI_ROOT"
docker compose run --rm dev bash -lc '
  cd $ROS2_WS_AI_ROOT/src/sutradhara_orchestrator &&
  python3 -m sutradhara_orchestrator.cli ros-bridge
'
```

### Terminal 3

Send a patrol mission using a sector ID:

```bash
cd "$ROS2_WS_AI_ROOT"
docker compose run --rm dev bash -lc '
  source /opt/ros/jazzy/setup.bash &&
  source $UNDERLAY_INSTALL/setup.bash &&
  source $ROS2_WS_AI_ROOT/install/setup.bash &&
  ros2 topic pub /orchestrator/mission_input std_msgs/msg/String "{data: '\''Patrol sector 1'\''}" -r 1 -t 5
'
```

Or send a patrol mission using a named operational area:

```bash
cd "$ROS2_WS_AI_ROOT"
docker compose run --rm dev bash -lc '
  source /opt/ros/jazzy/setup.bash &&
  source $UNDERLAY_INSTALL/setup.bash &&
  source $ROS2_WS_AI_ROOT/install/setup.bash &&
  ros2 topic pub /orchestrator/mission_input std_msgs/msg/String "{data: '\''Patrol the inverter yard'\''}" -r 1 -t 5
'
```

### Optional Observability

Watch the task command emitted by the orchestrator:

```bash
ros2 topic echo /orchestrator/task_command
```

Watch the trajectory published by mission control:

```bash
ros2 topic echo /px4_1/trajectory_upload
```

Watch PX4 local position:

```bash
ros2 topic echo /px4_1/fmu/out/vehicle_local_position
```

Expected behavior:

- the orchestrator emits a `PATROL` task with `target.kind = SECTOR_ID`
- `mission_control_node` resolves the sector to a configured patrol route
- the UAV takes off and flies the patrol path for that sector

### Local non-Docker equivalent

If you are not using Docker, the same flow still works with the local host setup:

1. launch `inspection_multi_robot_demo.launch.py`
2. run `uv run python -m sutradhara_orchestrator.cli ros-bridge`
3. publish `/orchestrator/mission_input`

## How Everything Fits Together

The pieces are separated intentionally:

- [`worlds/solar_farm_world.sdf`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/worlds/solar_farm_world.sdf)
  - defines the physical site layout
- [`models/`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/models)
  - defines reusable infrastructure building blocks
- [`config/assets.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/assets.yaml)
  - defines named inspectable objects and coordinates
- [`config/sectors.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/sectors.yaml)
  - defines planning sectors and their default patrol routes
- [`config/routes.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml)
  - defines repeatable route geometry for UAV missions
- [`launch/solar_farm_world.launch.py`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/launch/solar_farm_world.launch.py)
  - starts the world with the correct model resource path

This makes the package easy to extend:

- if the site layout changes, update the world file
- if an infrastructure component should be reused, update or add a model
- if you add new inspectable targets, update `assets.yaml`
- if you change mission geometry, update `routes.yaml`

## Next Integration Step

The next practical step is to connect sector-based mission intent from the orchestrator to the new mission-control route resolver so the UAV can patrol the solar farm by sector without hardcoded shell-script waypoints.

## Patrol Command Convention

For the current MVP, sector patrol uses the existing `TaskCommand` message without adding a new field yet.

The convention is:

- `task.task_type = PATROL`
- `task.target.kind = SECTOR_ID`
- `task.target.sector_id = <sector_id>`

Example:

```bash
ros2 topic pub --once /orchestrator/task_command robot_control_interfaces/msg/TaskCommand "{
  mission_id: 'mission_sector_patrol',
  task_id: 'task_sector_1',
  command_id: 'cmd_sector_1',
  robot_id: 'px4_1',
  type: 0,
  priority: 50,
  task: {
    task_type: 3,
    target: {
      frame: 'map',
      kind: 3,
      points: [],
      asset_id: '',
      sector_id: 'sector_1'
    },
    constraints: {
      safety_radius_m: 0.0,
      min_battery_pct_to_start: 0.0,
      require_sensors: []
    },
    success_criteria: {
      criteria: ['SECTOR_PATROL_COMPLETE']
    }
  }
}"
```

`mission_control_node` resolves `sector_1` to the configured patrol route from [`config/sectors.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/sectors.yaml) and [`config/routes.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml), then publishes the resulting `PoseArray` to the UAV.

## MVP vs Future Autonomy

The long-term goal for this project is not to rely on hardcoded assets or hardcoded routes.

The intended end state is:

- the user provides only a mission input
- the system interprets that mission
- the robot navigates autonomously
- the robot detects anomalies directly from sensor data
- the system reports findings without predefined inspection targets or manually authored paths

The current stack is not there yet. Right now it does not have:

- perception-driven anomaly detection
- semantic world understanding from live sensing
- dynamic viewpoint planning
- fully autonomous route generation from mission input alone

For the MVP, this package hardcodes two things in a structured way:

- [`config/assets.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/assets.yaml)
  - hardcoded semantic knowledge of what important infrastructure exists in the world and where it is
- [`config/routes.yaml`](/home/shravan/Projects/ros2_ws_ai/src/inspection_sim/config/routes.yaml)
  - hardcoded inspection flight paths that make the demo executable now

This is intentional.

Instead of burying assumptions inside shell scripts or C++ logic, the assumptions are stored as explicit data:

- the world provides geometry
- `assets.yaml` provides semantic meaning
- `routes.yaml` provides mission geometry

That makes the MVP useful now and replaceable later.

Expected evolution:

1. `assets.yaml` starts as prior knowledge or a digital twin of the site, then later gets updated or validated by perception.
2. `routes.yaml` starts as scripted patrol templates, then later gets replaced by planner-generated trajectories.
3. mission input eventually maps directly to asset selection, anomaly search, and autonomous motion instead of choosing a predefined route.

So yes, in the current MVP these files intentionally hardcode information that the autonomy stack should eventually infer or generate on its own.
