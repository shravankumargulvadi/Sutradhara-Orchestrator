from dataclasses import dataclass
from typing import ClassVar

@dataclass
class TaskAck:
    """
    Mirrors TaskAck.msg: Robot → Orchestrator
    """
    # Decision constants
    ACCEPTED: ClassVar[int] = 0
    REJECTED: ClassVar[int] = 1
    ACK_CANCELLED: ClassVar[int] = 2

    # Reject reason constants
    REASON_NONE: ClassVar[int] = 0
    REASON_LOW_BATTERY: ClassVar[int] = 1
    REASON_CAPABILITY_MISSING: ClassVar[int] = 2
    REASON_BUSY: ClassVar[int] = 3
    REASON_TARGET_INVALID: ClassVar[int] = 4
    REASON_SAFETY_CONSTRAINT: ClassVar[int] = 5
    REASON_INTERNAL_ERROR: ClassVar[int] = 6

    mission_id: str
    robot_id: str
    task_id: str
    command_id: str
    decision: int = 0
    reject_reason_code: int = 0
    reject_reason_detail: str = ""

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "command_id": self.command_id,
            "decision": self.decision,
            "reject_reason_code": self.reject_reason_code,
            "reject_reason_detail": self.reject_reason_detail
        }
