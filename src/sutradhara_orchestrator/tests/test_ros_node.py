import pytest

pytest.importorskip("rclpy")
pytest.importorskip("robot_control_interfaces.msg")

from robot_control_interfaces.msg import TaskAck as RosTaskAck
from robot_control_interfaces.msg import TaskUpdate as RosTaskUpdate

from sutradhara_orchestrator.ros_node import OrchestratorRosNode
from sutradhara_orchestrator.pubsub.broker import broker


def test_build_task_target_serializes_sector_id():
    node = object.__new__(OrchestratorRosNode)

    target_msg = node._build_task_target(
        {
            "frame": "map",
            "kind": 3,
            "asset_id": "",
            "sector_id": "sector_2",
            "points": [],
        }
    )

    assert target_msg.kind == 3
    assert target_msg.sector_id == "sector_2"
    assert target_msg.asset_id == ""


def test_task_ack_is_forwarded_to_broker(monkeypatch):
    node = object.__new__(OrchestratorRosNode)
    published = []
    monkeypatch.setattr(broker, "publish", lambda topic, payload: published.append((topic, payload)))

    msg = RosTaskAck()
    msg.mission_id = "mission_1"
    msg.robot_id = "px4_1"
    msg.task_id = "task_1"
    msg.command_id = "cmd_1"
    msg.decision = RosTaskAck.ACCEPTED
    msg.reject_reason_code = RosTaskAck.REASON_NONE
    msg.reject_reason_detail = ""

    node._on_task_ack(msg)

    assert published == [(
        "task_ack",
        {
            "mission_id": "mission_1",
            "robot_id": "px4_1",
            "task_id": "task_1",
            "command_id": "cmd_1",
            "decision": RosTaskAck.ACCEPTED,
            "reject_reason_code": RosTaskAck.REASON_NONE,
            "reject_reason_detail": "",
        },
    )]


def test_task_update_is_forwarded_to_broker(monkeypatch):
    node = object.__new__(OrchestratorRosNode)
    published = []
    monkeypatch.setattr(broker, "publish", lambda topic, payload: published.append((topic, payload)))

    msg = RosTaskUpdate()
    msg.mission_id = "mission_1"
    msg.robot_id = "px4_1"
    msg.task_id = "task_1"
    msg.status = RosTaskUpdate.STATUS_COMPLETED
    msg.progress_pct = 100.0
    msg.status_detail = "Patrol complete"
    msg.timestamp = "2026-03-29T12:00:00"

    node._on_task_update(msg)

    assert published == [(
        "task_update",
        {
            "mission_id": "mission_1",
            "robot_id": "px4_1",
            "task_id": "task_1",
            "status": RosTaskUpdate.STATUS_COMPLETED,
            "progress_pct": 100.0,
            "status_detail": "Patrol complete",
            "timestamp": "2026-03-29T12:00:00",
        },
    )]
