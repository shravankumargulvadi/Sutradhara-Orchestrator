import json
import queue
import threading
import time
import uuid
from typing import Any, Dict

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from robot_control_interfaces.msg import CapabilityProfile as RosCapabilityProfile
from robot_control_interfaces.msg import Point2D as RosPoint2D
from robot_control_interfaces.msg import RobotState as RosRobotState
from robot_control_interfaces.msg import TaskAck as RosTaskAck
from robot_control_interfaces.msg import TaskCommand as RosTaskCommand
from robot_control_interfaces.msg import TaskConstraints as RosTaskConstraints
from robot_control_interfaces.msg import TaskSpec as RosTaskSpec
from robot_control_interfaces.msg import TaskSuccessCriteria as RosTaskSuccessCriteria
from robot_control_interfaces.msg import TaskTarget as RosTaskTarget
from robot_control_interfaces.msg import TaskUpdate as RosTaskUpdate

from .messages.mission_input import MissionInput
from .orchestrator.agentic_ai import AgenticAI
from .pubsub.broker import broker


class OrchestratorRosNode(Node):
    def __init__(self, skills_dir: str | None = None) -> None:
        super().__init__("sutradhara_orchestrator")

        self.declare_parameter("skills_dir", skills_dir or "")
        resolved_skills_dir = self.get_parameter("skills_dir").get_parameter_value().string_value or None

        self._task_command_queue: "queue.Queue[RosTaskCommand]" = queue.Queue()
        self._mission_result_queue: "queue.Queue[String]" = queue.Queue()
        self._shutdown_lock = threading.Lock()
        self._shutdown = False

        self._orchestrator = AgenticAI(skills_dir=resolved_skills_dir)

        self._task_command_pub = self.create_publisher(RosTaskCommand, "/orchestrator/task_command", 10)
        self._mission_result_pub = self.create_publisher(String, "/orchestrator/mission_result", 10)

        self._mission_input_sub = self.create_subscription(
            String,
            "/orchestrator/mission_input",
            self._on_mission_input,
            10,
        )
        self._capability_sub = self.create_subscription(
            RosCapabilityProfile,
            "/orchestrator/capability_profile",
            self._on_capability_profile,
            10,
        )
        self._robot_state_sub = self.create_subscription(
            RosRobotState,
            "/orchestrator/robot_state",
            self._on_robot_state,
            10,
        )
        self._task_ack_sub = self.create_subscription(
            RosTaskAck,
            "/orchestrator/task_ack",
            self._on_task_ack,
            10,
        )
        self._task_update_sub = self.create_subscription(
            RosTaskUpdate,
            "/orchestrator/task_update",
            self._on_task_update,
            10,
        )

        self._flush_timer = self.create_timer(0.1, self._flush_broker_outputs)

        broker.subscribe("task_command", self._on_broker_task_command)
        broker.subscribe("mission_result", self._on_broker_mission_result)

        self.get_logger().info("ROS bridge ready. Listening on /orchestrator/mission_input")

    def destroy_node(self) -> bool:
        with self._shutdown_lock:
            if not self._shutdown:
                self._shutdown = True
                if hasattr(self._orchestrator, "shutdown"):
                    self._orchestrator.shutdown()
        return super().destroy_node()

    def _on_mission_input(self, msg: String) -> None:
        description = msg.data.strip()
        if not description:
            self.get_logger().warn("Ignoring empty mission input")
            return

        mission = MissionInput(
            mission_id=f"mission_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            description=description,
        )
        self.get_logger().info(f"Submitting mission from ROS input: {mission.mission_id}")
        self._orchestrator.submit_mission(mission)

    def _on_capability_profile(self, msg: RosCapabilityProfile) -> None:
        broker.publish(
            "capability_profile",
            {
                "robot_id": msg.robot_id,
                "platform": msg.platform,
                "max_speed_mps": msg.max_speed_mps,
                "max_run_time_s": msg.max_run_time_s,
                "sensors": list(msg.sensors),
                "task_types_supported": list(msg.task_types_supported),
            },
        )

    def _on_robot_state(self, msg: RosRobotState) -> None:
        broker.publish(
            "robot_state",
            {
                "robot_id": msg.robot_id,
                "mission_id": msg.mission_id,
                "current_task_id": msg.current_task_id,
                "x_m": msg.x_m,
                "y_m": msg.y_m,
                "yaw_rad": msg.yaw_rad,
                "z_m": msg.z_m,
                "velocity_mps": msg.velocity_mps,
                "battery_pct": msg.battery_pct,
                "health_status": msg.health_status,
                "faults": list(msg.faults),
                "availability_status": msg.availability_status,
                "heartbeat": msg.heartbeat,
            },
        )

    def _on_task_ack(self, msg: RosTaskAck) -> None:
        broker.publish(
            "task_ack",
            {
                "mission_id": msg.mission_id,
                "robot_id": msg.robot_id,
                "task_id": msg.task_id,
                "command_id": msg.command_id,
                "decision": msg.decision,
                "reject_reason_code": msg.reject_reason_code,
                "reject_reason_detail": msg.reject_reason_detail,
            },
        )

    def _on_task_update(self, msg: RosTaskUpdate) -> None:
        broker.publish(
            "task_update",
            {
                "mission_id": msg.mission_id,
                "robot_id": msg.robot_id,
                "task_id": msg.task_id,
                "status": msg.status,
                "progress_pct": msg.progress_pct,
                "status_detail": msg.status_detail,
                "timestamp": msg.timestamp,
            },
        )

    def _on_broker_task_command(self, msg_dict: Dict[str, Any]) -> None:
        ros_msg = RosTaskCommand()
        ros_msg.mission_id = msg_dict.get("mission_id", "")
        ros_msg.task_id = msg_dict.get("task_id", "")
        ros_msg.command_id = msg_dict.get("command_id", "")
        ros_msg.robot_id = msg_dict.get("robot_id", "")
        ros_msg.type = int(msg_dict.get("type", RosTaskCommand.ASSIGN))
        ros_msg.priority = int(msg_dict.get("priority", 50))
        ros_msg.task = self._build_task_spec(msg_dict.get("task") or {})
        self._task_command_queue.put(ros_msg)

    def _on_broker_mission_result(self, msg_dict: Dict[str, Any]) -> None:
        ros_msg = String()
        ros_msg.data = json.dumps(msg_dict)
        self._mission_result_queue.put(ros_msg)

    def _flush_broker_outputs(self) -> None:
        while not self._task_command_queue.empty():
            self._task_command_pub.publish(self._task_command_queue.get())

        while not self._mission_result_queue.empty():
            self._mission_result_pub.publish(self._mission_result_queue.get())

    def _build_task_spec(self, task_dict: Dict[str, Any]) -> RosTaskSpec:
        task_msg = RosTaskSpec()
        task_msg.task_type = int(task_dict.get("task_type", RosTaskSpec.INSPECT))
        task_msg.target = self._build_task_target(task_dict.get("target") or {})
        task_msg.constraints = self._build_constraints(task_dict.get("constraints") or {})
        success = RosTaskSuccessCriteria()
        success.criteria = list(task_dict.get("success_criteria", []))
        task_msg.success_criteria = success
        return task_msg

    def _build_task_target(self, target_dict: Dict[str, Any]) -> RosTaskTarget:
        target_msg = RosTaskTarget()
        target_msg.frame = target_dict.get("frame", "map")
        target_msg.kind = int(target_dict.get("kind", RosTaskTarget.POINT))
        target_msg.asset_id = target_dict.get("asset_id", "")
        target_msg.sector_id = target_dict.get("sector_id", "")
        target_msg.points = [self._build_point(point_dict) for point_dict in target_dict.get("points", [])]
        return target_msg

    def _build_constraints(self, constraints_dict: Dict[str, Any]) -> RosTaskConstraints:
        constraints_msg = RosTaskConstraints()
        constraints_msg.safety_radius_m = float(constraints_dict.get("safety_radius_m", 0.0))
        constraints_msg.min_battery_pct_to_start = float(
            constraints_dict.get("min_battery_pct_to_start", 0.0)
        )
        constraints_msg.require_sensors = list(constraints_dict.get("require_sensors", []))
        return constraints_msg

    @staticmethod
    def _build_point(point_dict: Dict[str, Any]) -> RosPoint2D:
        point = RosPoint2D()
        point.x = float(point_dict.get("x", 0.0))
        point.y = float(point_dict.get("y", 0.0))
        return point


def main() -> None:
    rclpy.init()
    node = OrchestratorRosNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
