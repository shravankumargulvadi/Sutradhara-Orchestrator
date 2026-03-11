# Sutradhara-Orchestrator

This workspace contains the new `robot_control` package which has a split robot-specific `manager` that runs onboard the robot and the `mission-control` subsystem which runs off-board and interfaces with the `AI-Agent-Orch`

## Scope

This workspace is currently validated for:
- Ubuntu 24.04 (Noble)
- ROS 2 Jazzy
- Gazebo Harmonic
- PX4 SITL with `gz_x500`
- Micro XRCE-DDS bridge
- `robot_control` nodes: `uav_manager` and `mission_control_node`

## Important underlay requirement

`robot_control` currently depends on `px4_msgs` from the original workspace:

`/home/shravan/Projects/ros2_ws`

That means you must source the original workspace as an underlay before building or running anything from `ros2_ws_ai`.

Build/run order for this workspace is:

```bash
source /opt/ros/jazzy/setup.bash
source /home/shravan/Projects/ros2_ws/install/setup.bash
source /home/shravan/Projects/ros2_ws_ai/install/setup.bash
```

If you skip the `ros2_ws` underlay, `robot_control` will not resolve `px4_msgs`.

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

ros2 run robot_control mission_control_node --ros-args -p drone_ids:="['/px4_0']"
```

Important:
- The executable was renamed to `mission_control_node`
- The parameter is still named `drone_ids` in code
- The expected value is the application namespace string, for example `'/px4_0'`

`mission_control_node` currently publishes the mission once after startup. It does not continuously republish.

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
- publishes a `geometry_msgs/msg/PoseArray` mission
- acts as a minimal base station / mission trigger

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

This will publish the same waypoint mission once to both:
- `/px4_1/trajectory_upload`
- `/px4_2/trajectory_upload`

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
  Make sure `uav_manager` is already running and the parameter is exactly:
  `-p drone_ids:="['/px4_0']"`

## Standalone later

If you want `ros2_ws_ai` to become fully standalone later, move or duplicate the required PX4 interface dependencies into this workspace, starting with:

- `px4_msgs`
- any future shared PX4 bridge packages or custom interfaces
