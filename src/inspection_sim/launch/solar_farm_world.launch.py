from pathlib import Path
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable


def generate_launch_description() -> LaunchDescription:
    package_share = Path(get_package_share_directory("inspection_sim"))
    world_path = package_share / "worlds" / "solar_farm_world.sdf"
    models_path = package_share / "models"

    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_path = str(models_path) if not existing_resource_path else f"{models_path}:{existing_resource_path}"

    return LaunchDescription(
        [
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            ExecuteProcess(
                cmd=["gz", "sim", "-r", str(world_path)],
                output="screen",
            ),
        ]
    )
