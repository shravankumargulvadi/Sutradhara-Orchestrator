from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from .task import Task, TaskStatus

class MissionStatus(Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class Mission:
    """
    Internal data model for a mission.
    """
    mission_id: str
    description: str
    status: MissionStatus = MissionStatus.CREATED
    final_response: Optional[str] = None
    
    tasks: Dict[str, Task] = field(default_factory=dict)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == status]

    def all_tasks_completed(self) -> bool:
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks.values())

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "description": self.description,
            "status": self.status.value,
            "task_count": len(self.tasks),
            "final_response": self.final_response
        }
