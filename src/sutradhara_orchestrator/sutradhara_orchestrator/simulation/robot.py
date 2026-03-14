import threading
import time
import random
import logging
from datetime import datetime
from ..pubsub.broker import broker
from ..messages.robot_state import RobotState
from ..messages.capability_profile import CapabilityProfile
from ..messages.task_command import TaskCommand
from ..messages.task_ack import TaskAck
from ..messages.task_update import TaskUpdate

logger = logging.getLogger(__name__)

class SimulatedRobot:
    """
    Base class for simulated robots (UAV/UGV).
    """
    def __init__(self, robot_id: str, platform: int, sensors: list[str], task_types: list[int]):
        self.robot_id = robot_id
        self.platform = platform
        self.sensors = sensors
        self.task_types = task_types
        
        self.battery_pct = 100.0
        self.health = RobotState.HEALTH_OK
        self.availability = RobotState.AVAIL_IDLE
        self.current_task_id = ""
        self.current_mission_id = ""
        
        self.x, self.y, self.z = 0.0, 0.0, 0.0
        self.stop_event = threading.Event()
        
        # Subscribe to task commands and faults
        broker.subscribe("task_command", self._on_task_command)
        broker.subscribe("fault_injection", self._on_fault)

    def _on_fault(self, fault_dict: dict):
        if fault_dict.get("robot_id") != self.robot_id:
            return
            
        fault_type = fault_dict.get("fault")
        logger.warning(f"[{self.robot_id}] Injected fault: {fault_type}")
        
        if fault_type == "OFFLINE":
            self.stop()
        elif fault_type == "FAILED":
            self.health = RobotState.HEALTH_FAILED
        elif fault_type == "LOW_BATTERY":
            self.battery_pct = 5.0

    def start(self):
        # 1. Advertise capabilities
        self.advertise()
        
        # 2. Start state streaming thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def advertise(self):
        profile = CapabilityProfile(
            robot_id=self.robot_id,
            platform=self.platform,
            sensors=self.sensors,
            task_types_supported=self.task_types,
            max_speed_mps=15.0 if self.platform == CapabilityProfile.PLATFORM_UAV else 2.0,
            max_run_time_s=1800.0
        )
        broker.publish("capability_profile", profile.to_dict())

    def _on_task_command(self, cmd_dict: dict):
        if cmd_dict.get("robot_id") != self.robot_id:
            return

        cmd_type = cmd_dict.get("type")
        task_id = cmd_dict.get("task_id")
        
        if cmd_type == TaskCommand.ASSIGN:
            self._handle_assign(cmd_dict)
        elif cmd_type == TaskCommand.CANCEL:
            self._handle_cancel(task_id)

    def _handle_assign(self, cmd_dict: dict):
        # Simplified logic: always accept if idle and has battery
        if self.availability != RobotState.AVAIL_IDLE:
            self._send_ack(cmd_dict, TaskAck.REJECTED, TaskAck.REASON_BUSY)
            return
        
        if self.battery_pct < 10.0:
            self._send_ack(cmd_dict, TaskAck.REJECTED, TaskAck.REASON_LOW_BATTERY)
            return

        self.current_task_id = cmd_dict.get("task_id")
        self.current_mission_id = cmd_dict.get("mission_id")
        # Ensure we are using the correct constant access
        self.availability = RobotState.AVAIL_BUSY
        
        self._send_ack(cmd_dict, TaskAck.ACCEPTED)
        
        # Start simulated execution
        threading.Thread(target=self._simulate_task, args=(self.current_task_id,), daemon=True).start()

    def _handle_cancel(self, task_id: str):
        if self.current_task_id == task_id:
            self.current_task_id = ""
            self.availability = RobotState.AVAIL_IDLE
            logger.info(f"[{self.robot_id}] Task {task_id} cancelled.")

    def _send_ack(self, cmd_dict: dict, decision: int, reason: int = 0):
        ack = TaskAck(
            mission_id=cmd_dict.get("mission_id"),
            robot_id=self.robot_id,
            task_id=cmd_dict.get("task_id"),
            command_id=cmd_dict.get("command_id"),
            decision=decision,
            reject_reason_code=reason
        )
        broker.publish("task_ack", ack.to_dict())

    def _simulate_task(self, task_id: str):
        # Simulate work
        for i in range(1, 11):
            if self.current_task_id != task_id: break
            time.sleep(1.0) # 10 seconds total
            
            action = "Executing"
            if i < 4: action = "Navigating to target"
            elif i < 8: action = f"Performing {self.robot_id} specialized sensing"
            else: action = "Finalizing operation"

            update = TaskUpdate(
                mission_id=self.current_mission_id,
                robot_id=self.robot_id,
                task_id=task_id,
                status=TaskUpdate.STATUS_IN_PROGRESS,
                progress_pct=i * 10.0,
                status_detail=action
            )
            broker.publish("task_update", update.to_dict())
            self.battery_pct -= 0.5

        if self.current_task_id == task_id:
            update = TaskUpdate(
                mission_id=self.current_mission_id,
                robot_id=self.robot_id,
                task_id=task_id,
                status=TaskUpdate.STATUS_COMPLETED,
                progress_pct=100.0,
                status_detail="Task successfully finished"
            )
            broker.publish("task_update", update.to_dict())
            self.availability = RobotState.AVAIL_IDLE
            self.current_task_id = ""

    def _run(self):
        while not self.stop_event.is_set():
            state = RobotState(
                robot_id=self.robot_id,
                mission_id=self.current_mission_id,
                current_task_id=self.current_task_id,
                battery_pct=self.battery_pct,
                health_status=self.health,
                availability_status=self.availability,
                x_m=self.x, y_m=self.y, z_m=self.z
            )
            broker.publish("robot_state", state.to_dict())
            time.sleep(1.0)

class SimulatedUAV(SimulatedRobot):
    def __init__(self, robot_id: str):
        super().__init__(
            robot_id=robot_id,
            platform=CapabilityProfile.PLATFORM_UAV,
            sensors=["RGB", "THERMAL"],
            task_types=[
                CapabilityProfile.TASK_INSPECT,
                CapabilityProfile.TASK_VERIFY,
                CapabilityProfile.TASK_PATROL,
                CapabilityProfile.TASK_RETURN_HOME
            ]
        )

class SimulatedUGV(SimulatedRobot):
    def __init__(self, robot_id: str):
        super().__init__(
            robot_id=robot_id,
            platform=CapabilityProfile.PLATFORM_AMR,
            sensors=["RGB", "LIDAR"],
            task_types=[
                CapabilityProfile.TASK_INSPECT,
                CapabilityProfile.TASK_VERIFY,
                CapabilityProfile.TASK_PATROL,
                CapabilityProfile.TASK_RETURN_HOME
            ]
        )
