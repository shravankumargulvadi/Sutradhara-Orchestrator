import pytest

pytest.importorskip("rclpy")
pytest.importorskip("robot_control_interfaces.msg")

from sutradhara_orchestrator.ros_node import OrchestratorRosNode


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
