from pathlib import Path
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable, TimerAction
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default)


def generate_launch_description() -> LaunchDescription:
    inspection_share = Path(get_package_share_directory("inspection_sim"))
    world_path = inspection_share / "worlds" / "solar_farm_world.sdf"
    inspection_models_path = inspection_share / "models"
    world_name = "solar_farm_demo"

    default_px4_dir = env_or_default("PX4_DIR", "/workspace/PX4-Autopilot")
    default_underlay_install = env_or_default("UNDERLAY_INSTALL", "/workspace/underlay/install")
    default_px4_models_path = env_or_default(
        "PX4_GZ_MODELS_PATH",
        f"{default_px4_dir}/Tools/simulation/gz/models",
    )
    default_px4_worlds_path = env_or_default(
        "PX4_GZ_WORLDS_PATH",
        f"{default_px4_dir}/Tools/simulation/gz/worlds",
    )
    default_px4_bin = env_or_default(
        "PX4_BIN",
        f"{default_px4_dir}/build/px4_sitl_default/bin/px4",
    )
    default_xrce_install = env_or_default("XRCE_INSTALL", "/workspace/px4_ros_uxrce_dds_ws/install")
    default_xrce_agent = env_or_default(
        "MICRO_XRCE_AGENT_BIN",
        f"{default_xrce_install}/microxrcedds_agent/bin/MicroXRCEAgent",
    )
    default_xrce_agent_lib_dir = env_or_default(
        "MICRO_XRCE_AGENT_LIB_DIR",
        f"{default_xrce_install}/microxrcedds_agent/lib",
    )

    px4_dir = LaunchConfiguration("px4_dir")
    px4_bin = LaunchConfiguration("px4_bin")
    px4_gz_models_path = LaunchConfiguration("px4_gz_models_path")
    px4_gz_worlds_path = LaunchConfiguration("px4_gz_worlds_path")
    underlay_install = LaunchConfiguration("underlay_install")
    micro_xrce_agent_bin = LaunchConfiguration("micro_xrce_agent_bin")
    micro_xrce_agent_lib_dir = LaunchConfiguration("micro_xrce_agent_lib_dir")
    px4_autostart = LaunchConfiguration("px4_autostart")
    flight_altitude_m = LaunchConfiguration("flight_altitude_m")
    drone_id = LaunchConfiguration("drone_id")
    gz_model_pose = LaunchConfiguration("gz_model_pose")
    wait_before_px4_s = LaunchConfiguration("wait_before_px4_s")
    wait_before_ros_nodes_s = LaunchConfiguration("wait_before_ros_nodes_s")
    resource_path = [
        str(inspection_models_path),
        ":",
        px4_gz_models_path,
        ":",
        px4_gz_worlds_path,
        ":",
        EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value=""),
    ]
    underlay_lib_path = PathJoinSubstitution([underlay_install, "px4_msgs", "lib"])
    merged_ld_library_path = [
        underlay_lib_path,
        ":",
        micro_xrce_agent_lib_dir,
        ":",
        EnvironmentVariable("LD_LIBRARY_PATH", default_value=""),
    ]
    merged_ament_prefix_path = [underlay_install, ":", EnvironmentVariable("AMENT_PREFIX_PATH", default_value="")]

    return LaunchDescription(
        [
            DeclareLaunchArgument("px4_dir", default_value=default_px4_dir),
            DeclareLaunchArgument(
                "px4_bin",
                default_value=default_px4_bin,
            ),
            DeclareLaunchArgument("px4_gz_models_path", default_value=default_px4_models_path),
            DeclareLaunchArgument("px4_gz_worlds_path", default_value=default_px4_worlds_path),
            DeclareLaunchArgument("underlay_install", default_value=default_underlay_install),
            DeclareLaunchArgument("micro_xrce_agent_bin", default_value=default_xrce_agent),
            DeclareLaunchArgument("micro_xrce_agent_lib_dir", default_value=default_xrce_agent_lib_dir),
            DeclareLaunchArgument("px4_autostart", default_value="4001"),
            DeclareLaunchArgument("flight_altitude_m", default_value="8.0"),
            DeclareLaunchArgument("drone_id", default_value="1"),
            DeclareLaunchArgument("gz_model_pose", default_value="0,0,1.0,0,0,0"),
            DeclareLaunchArgument("wait_before_px4_s", default_value="2.0"),
            DeclareLaunchArgument("wait_before_ros_nodes_s", default_value="10.0"),
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            SetEnvironmentVariable("LD_LIBRARY_PATH", merged_ld_library_path),
            SetEnvironmentVariable("AMENT_PREFIX_PATH", merged_ament_prefix_path),
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
                            "PX4_GZ_WORLD": world_name,
                            "PX4_GZ_MODEL_NAME": "x500_1",
                            "PX4_GZ_MODELS": px4_gz_models_path,
                            "PX4_GZ_WORLDS": px4_gz_worlds_path,
                            "GZ_SIM_RESOURCE_PATH": resource_path,
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
