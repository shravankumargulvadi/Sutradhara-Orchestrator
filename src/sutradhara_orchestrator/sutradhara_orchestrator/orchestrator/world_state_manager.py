import time
import logging
from typing import Dict, List, Optional, Any
from ..messages.robot_state import RobotState
from ..messages.capability_profile import CapabilityProfile
from ..models.robot import Robot
from ..pubsub.broker import broker
from ..utils.config_manager import config

logger = logging.getLogger(__name__)

class WorldStateManager:
    """
    Tracks the real-time state and capabilities of all robots in the system.
    """
    def __init__(self, heartbeat_timeout_s: Optional[float] = None):
        self.heartbeat_timeout = heartbeat_timeout_s or config.get("simulation.heartbeat_timeout_s", 5.0)
        self.robots: Dict[str, Robot] = {}
        
        # Subscribe to robot discovery and state updates
        broker.subscribe("capability_profile", self._on_capability_profile)
        broker.subscribe("robot_state", self._on_robot_state)

    def _on_capability_profile(self, profile_dict: dict):
        profile = CapabilityProfile(**profile_dict)
        robot_id = profile.robot_id
        
        if robot_id not in self.robots:
            self.robots[robot_id] = Robot(robot_id=robot_id)
            logger.info(f"Discovered new robot: {robot_id}")
        
        self.robots[robot_id].capabilities = profile
        logger.info(f"Discovered/Updated capabilities for robot: {robot_id}")

    def _on_robot_state(self, state_dict: dict):
        state = RobotState(**state_dict)
        robot_id = state.robot_id
        
        if robot_id in self.robots:
            self.robots[robot_id].last_state = state
            self.robots[robot_id].last_heartbeat = time.time()
        else:
            # Optionally handle state update for undiscovered robot
            pass

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        return self.robots.get(robot_id)

    def get_active_robots(self) -> List[Robot]:
        """Returns robots that have sent a heartbeat within the timeout period."""
        now = time.time()
        return [
            r for r in self.robots.values()
            if r.last_heartbeat and (now - r.last_heartbeat) < self.heartbeat_timeout
        ]

    def get_world_summary(self) -> dict:
        active = self.get_active_robots()
        return {
            "count": len(active),
            "robots": [r.to_dict() for r in active]
        }
