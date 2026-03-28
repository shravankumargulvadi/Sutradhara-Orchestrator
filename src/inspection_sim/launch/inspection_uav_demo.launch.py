from pathlib import Path
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    inspection_share = Path(get_package_share_directory("inspection_sim"))
    world_path = inspection_share / "worlds" / "solar_farm_world.sdf"
    inspection_models_path = inspection_share / "models"

    default_px4_dir = "/home/shravan/Projects/PX4-Autopilot"
    default_xrce_agent = (
        "/home/shravan/Projects/px4_ros_uxrce_dds_ws/install/"
        "microxrcedds_agent/bin/MicroXRCEAgent"
    )

    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_path = (
        str(inspection_models_path)
        if not existing_resource_path
        else f"{inspection_models_path}:{existing_resource_path}"
    )

    px4_dir = LaunchConfiguration("px4_dir")
    px4_bin = LaunchConfiguration("px4_bin")
    micro_xrce_agent_bin = LaunchConfiguration("micro_xrce_agent_bin")
    px4_autostart = LaunchConfiguration("px4_autostart")
    flight_altitude_m = LaunchConfiguration("flight_altitude_m")
    drone_id = LaunchConfiguration("drone_id")
    gz_model_pose = LaunchConfiguration("gz_model_pose")
    wait_before_px4_s = LaunchConfiguration("wait_before_px4_s")
    wait_before_ros_nodes_s = LaunchConfiguration("wait_before_ros_nodes_s")

    return LaunchDescription(
        [
            DeclareLaunchArgument("px4_dir", default_value=default_px4_dir),
            DeclareLaunchArgument(
                "px4_bin",
                default_value=f"{default_px4_dir}/build/px4_sitl_default/bin/px4",
            ),
            DeclareLaunchArgument("micro_xrce_agent_bin", default_value=default_xrce_agent),
            DeclareLaunchArgument("px4_autostart", default_value="4001"),
            DeclareLaunchArgument("flight_altitude_m", default_value="8.0"),
            DeclareLaunchArgument("drone_id", default_value="1"),
            DeclareLaunchArgument("gz_model_pose", default_value="0,0,0.2,0,0,0"),
            DeclareLaunchArgument("wait_before_px4_s", default_value="2.0"),
            DeclareLaunchArgument("wait_before_ros_nodes_s", default_value="10.0"),
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            ExecuteProcess(
                cmd=["gz", "sim", "-r", str(world_path)],
                output="screen",
            ),
            ExecuteProcess(
                cmd=[micro_xrce_agent_bin, "udp4", "-p", "8888"],
                output="screen",
            ),
            TimerAction(
                period=wait_before_px4_s,
                actions=[
                    ExecuteProcess(
                        cmd=[px4_bin, "-i", drone_id],
                        cwd=px4_dir,
                        output="screen",
                        additional_env={
                            "PX4_GZ_STANDALONE": "1",
                            "PX4_SYS_AUTOSTART": px4_autostart,
                            "PX4_SIM_MODEL": "gz_x500",
                            "PX4_GZ_MODEL_POSE": gz_model_pose,
                        },
                    )
                ],
            ),
            TimerAction(
                period=wait_before_ros_nodes_s,
                actions=[
                    Node(
                        package="robot_control",
                        executable="uav_manager",
                        output="screen",
                        parameters=[{"drone_id": drone_id}],
                    ),
                    Node(
                        package="robot_control",
                        executable="mission_control_node",
                        output="screen",
                        parameters=[{"flight_altitude_m": flight_altitude_m}],
                    ),
                ],
            ),
        ]
    )
