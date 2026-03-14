from dataclasses import dataclass
from typing import ClassVar
from datetime import datetime

@dataclass
class TaskUpdate:
    """
    Mirrors TaskUpdate.msg: Robot → Orchestrator progress reports
    """
    # Status constants
    STATUS_IN_PROGRESS: ClassVar[int] = 0
    STATUS_COMPLETED: ClassVar[int] = 1
    STATUS_FAILED: ClassVar[int] = 2
    STATUS_ABORTED: ClassVar[int] = 3

    mission_id: str
    robot_id: str
    task_id: str
    status: int = 0
    progress_pct: float = 0.0
    status_detail: str = ""
    timestamp: datetime = datetime.now()

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "status_detail": self.status_detail,
            "timestamp": self.timestamp.isoformat()
        }
