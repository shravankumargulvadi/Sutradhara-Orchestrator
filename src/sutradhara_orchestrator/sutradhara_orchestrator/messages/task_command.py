from dataclasses import dataclass, field
from typing import List, Optional, ClassVar
from datetime import datetime

@dataclass
class Point2D:
    x: float
    y: float
    z: float = 0.0

@dataclass
class TaskTarget:
    POINT: ClassVar[int] = 0
    REGION: ClassVar[int] = 1
    ASSET_ID: ClassVar[int] = 2
    SECTOR_ID: ClassVar[int] = 3

    frame: str = "map"
    kind: int = 0
    points: List[Point2D] = field(default_factory=list)
    asset_id: str = ""
    sector_id: str = ""
    def to_dict(self) -> dict:
        return {
            "frame": self.frame,
            "kind": self.kind,
            "points": [{"x": p.x, "y": p.y, "z": p.z} for p in self.points],
            "asset_id": self.asset_id,
            "sector_id": self.sector_id,
        }

@dataclass
class TaskConstraints:
    safety_radius_m: float = 0.0
    min_battery_pct_to_start: float = 0.0
    require_sensors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "safety_radius_m": self.safety_radius_m,
            "min_battery_pct_to_start": self.min_battery_pct_to_start,
            "require_sensors": self.require_sensors
        }

@dataclass
class TaskSpec:
    INSPECT: ClassVar[int] = 0
    VERIFY: ClassVar[int] = 1
    REVISIT: ClassVar[int] = 2
    PATROL: ClassVar[int] = 3
    RETURN_HOME: ClassVar[int] = 4

    task_type: int = 0
    target: TaskTarget = field(default_factory=TaskTarget)
    constraints: TaskConstraints = field(default_factory=TaskConstraints)
    success_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "target": self.target.to_dict(),
            "constraints": self.constraints.to_dict(),
            "success_criteria": self.success_criteria
        }

@dataclass
class TaskCommand:
    """
    Mirrors TaskCommand.msg: Orchestrator → Robot
    """
    ASSIGN: ClassVar[int] = 0
    CANCEL: ClassVar[int] = 1
    PAUSE: ClassVar[int] = 2
    RESUME: ClassVar[int] = 3
    UPDATE_PRIORITY: ClassVar[int] = 4

    mission_id: str
    task_id: str
    command_id: str
    robot_id: str
    type: int = 0
    priority: int = 50
    task: Optional[TaskSpec] = None

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "command_id": self.command_id,
            "robot_id": self.robot_id,
            "type": self.type,
            "priority": self.priority,
            "task": self.task.to_dict() if self.task else None
        }
