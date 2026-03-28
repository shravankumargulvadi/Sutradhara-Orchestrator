from pathlib import Path
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable


def generate_launch_description() -> LaunchDescription:
    package_share = Path(get_package_share_directory("inspection_sim"))
    world_path = package_share / "worlds" / "solar_farm_world.sdf"
    models_path = package_share / "models"
    px4_dir = Path("/home/shravan/Projects/PX4-Autopilot")
    px4_models_path = px4_dir / "Tools" / "simulation" / "gz" / "models"
    px4_worlds_path = px4_dir / "Tools" / "simulation" / "gz" / "worlds"

    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_entries = [str(models_path), str(px4_models_path), str(px4_worlds_path)]
    if existing_resource_path:
        resource_entries.append(existing_resource_path)
    resource_path = ":".join(resource_entries)

    return LaunchDescription(
        [
            SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
            ExecuteProcess(
                cmd=["gz", "sim", "-r", str(world_path)],
                output="screen",
            ),
        ]
    )
