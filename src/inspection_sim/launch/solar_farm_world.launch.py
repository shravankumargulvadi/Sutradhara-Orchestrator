from pathlib import Path
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default)


def generate_launch_description() -> LaunchDescription:
    package_share = Path(get_package_share_directory("inspection_sim"))
    world_path = package_share / "worlds" / "solar_farm_world.sdf"
    models_path = package_share / "models"
    default_px4_dir = env_or_default("PX4_DIR", "/opt/px4")
    default_px4_models_path = env_or_default(
        "PX4_GZ_MODELS_PATH",
        f"{default_px4_dir}/Tools/simulation/gz/models",
    )
    default_px4_worlds_path = env_or_default(
        "PX4_GZ_WORLDS_PATH",
        f"{default_px4_dir}/Tools/simulation/gz/worlds",
    )
    px4_models_path = LaunchConfiguration("px4_gz_models_path")
    px4_worlds_path = LaunchConfiguration("px4_gz_worlds_path")
    resource_path = [
        str(models_path),
        ":",
        px4_models_path,
        ":",
        px4_worlds_path,
        ":",
        EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value=""),
    ]

    return LaunchDescription(
        [
            DeclareLaunchArgument("px4_gz_models_path", default_value=default_px4_models_path),
            DeclareLaunchArgument("px4_gz_worlds_path", default_value=default_px4_worlds_path),
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            ExecuteProcess(
                cmd=["gz", "sim", "-r", str(world_path)],
                output="screen",
            ),
        ]
    )
