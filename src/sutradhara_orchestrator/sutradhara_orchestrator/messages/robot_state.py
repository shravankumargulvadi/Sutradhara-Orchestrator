from dataclasses import dataclass, field
from typing import List, Optional, ClassVar
from datetime import datetime

@dataclass
class RobotState:
    """
    Mirrors RobotState.msg: published by each robot at 1 Hz
    """
    # Health constants
    HEALTH_OK: ClassVar[int] = 0
    HEALTH_DEGRADED: ClassVar[int] = 1
    HEALTH_FAILED: ClassVar[int] = 2

    # Availability constants
    AVAIL_IDLE: ClassVar[int] = 0
    AVAIL_BUSY: ClassVar[int] = 1
    AVAIL_RETURNING_HOME: ClassVar[int] = 2
    AVAIL_CHARGING: ClassVar[int] = 3
    AVAIL_OFFLINE: ClassVar[int] = 4

    robot_id: str
    mission_id: str = ""
    current_task_id: str = ""

    # Pose
    x_m: float = 0.0
    y_m: float = 0.0
    yaw_rad: float = 0.0
    z_m: float = 0.0

    velocity_mps: float = 0.0
    battery_pct: float = 100.0  # 0..100

    health_status: int = 0
    faults: List[str] = field(default_factory=list)
    availability_status: int = 0

    heartbeat: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "mission_id": self.mission_id,
            "current_task_id": self.current_task_id,
            "x_m": self.x_m,
            "y_m": self.y_m,
            "yaw_rad": self.yaw_rad,
            "z_m": self.z_m,
            "velocity_mps": self.velocity_mps,
            "battery_pct": self.battery_pct,
            "health_status": self.health_status,
            "faults": self.faults,
            "availability_status": self.availability_status,
            "heartbeat": self.heartbeat,
            "timestamp": self.timestamp.isoformat()
        }
