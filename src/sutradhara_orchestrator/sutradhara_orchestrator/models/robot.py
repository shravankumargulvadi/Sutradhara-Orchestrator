from dataclasses import dataclass, field
from typing import List, Optional
from ..messages.robot_state import RobotState
from ..messages.capability_profile import CapabilityProfile

@dataclass
class Robot:
    """
    Internal data model for a robot.
    """
    robot_id: str
    capabilities: Optional[CapabilityProfile] = None
    last_state: Optional[RobotState] = None
    
    active_task_id: Optional[str] = None
    assigned_task_ids: List[str] = field(default_factory=list)

    def is_idle(self) -> bool:
        if not self.last_state:
            return False
        return self.last_state.availability_status == self.last_state.AVAIL_IDLE

    def has_capability(self, task_type: int) -> bool:
        if not self.capabilities:
            return False
        return task_type in self.capabilities.task_types_supported

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "platform": self.capabilities.platform if self.capabilities else None,
            "sensors": self.capabilities.sensors if self.capabilities else [],
            "task_types": self.capabilities.task_types_supported if self.capabilities else [],
            "idle": self.is_idle(),
            "active_task": self.active_task_id
        }
