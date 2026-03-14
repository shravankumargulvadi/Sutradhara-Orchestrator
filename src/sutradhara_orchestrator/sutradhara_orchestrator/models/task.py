from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
from ..messages.task_command import TaskSpec
from ..messages.task_update import TaskUpdate

class TaskStatus(Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

@dataclass
class Task:
    """
    Internal data model for a task.
    """
    task_id: str
    mission_id: str
    spec: TaskSpec
    priority: int = 50
    dependencies: List[str] = field(default_factory=list)
    
    assigned_robot_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    progress_pct: float = 0.0
    status_detail: str = ""
    
    updates: List[TaskUpdate] = field(default_factory=list)

    def is_executable(self, completed_tasks: List[str]) -> bool:
        """Checks if all dependencies are met."""
        return all(dep in completed_tasks for dep in self.dependencies)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "status": self.status.value,
            "assigned_robot_id": self.assigned_robot_id,
            "progress_pct": self.progress_pct,
            "spec": self.spec.to_dict()
        }
