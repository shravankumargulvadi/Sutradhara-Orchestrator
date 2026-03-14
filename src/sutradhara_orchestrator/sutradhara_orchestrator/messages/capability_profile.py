from dataclasses import dataclass, field
from typing import List, ClassVar

@dataclass
class CapabilityProfile:
    """
    Mirrors CapabilityProfile.msg: advertised by each robot on startup
    """
    # Platform constants
    PLATFORM_UAV: ClassVar[int] = 0
    PLATFORM_AMR: ClassVar[int] = 1

    # Task type constants
    TASK_INSPECT: ClassVar[int] = 0
    TASK_VERIFY: ClassVar[int] = 1
    TASK_REVISIT: ClassVar[int] = 2
    TASK_PATROL: ClassVar[int] = 3
    TASK_RETURN_HOME: ClassVar[int] = 4

    robot_id: str
    platform: int = 0

    # Locomotion
    max_speed_mps: float = 0.0
    max_run_time_s: float = 0.0

    # Sensors
    sensors: List[str] = field(default_factory=list)  # e.g. ["RGB", "THERMAL", "LIDAR"]

    # Supported task types
    task_types_supported: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "platform": self.platform,
            "max_speed_mps": self.max_speed_mps,
            "max_run_time_s": self.max_run_time_s,
            "sensors": self.sensors,
            "task_types_supported": self.task_types_supported
        }
