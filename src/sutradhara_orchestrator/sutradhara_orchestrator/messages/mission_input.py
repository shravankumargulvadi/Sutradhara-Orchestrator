from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from .task_command import Point2D

@dataclass
class MissionInput:
    """
    Mirrors MissionInput.msg: User → Orchestrator
    """
    mission_id: str
    description: str            # natural language or structured text

    # Objectives
    objective_types: List[str] = field(default_factory=list)  # e.g. ["INSPECT", "VERIFY"]
    objective_locations: List[Point2D] = field(default_factory=list)
    asset_ids: List[str] = field(default_factory=list)

    # Constraints
    deadline_sec: float = 0.0
    priority: int = 50

    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "description": self.description,
            "objective_types": self.objective_types,
            "deadline_sec": self.deadline_sec,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat()
        }
