import time
import pytest
from unittest.mock import patch, MagicMock
from sutradhara_orchestrator.orchestrator.agentic_ai import AgenticAI
from sutradhara_orchestrator.simulation.robot import SimulatedUAV, SimulatedRobot
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.models.mission import MissionStatus
from sutradhara_orchestrator.models.task import TaskStatus
from sutradhara_orchestrator.pubsub.broker import broker

@patch("litellm.completion")
def test_self_healing_reallocation(mock_completion, tmp_path):
    # Setup skills
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "inspection").mkdir()
    (skills_dir / "inspection" / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\ncontent")
    
    # 1. Start Orchestrator
    orchestrator = AgenticAI(skills_dir=str(skills_dir))
    
    # 2. Start two Robots
    uav1 = SimulatedUAV("uav_1")
    uav2 = SimulatedUAV("uav_2")
    uav1.start()
    uav2.start()
    
    time.sleep(2.0) # Wait for discovery
    
    # 3. Mock LLM for 1 task
    mock_select = MagicMock()
    mock_select.choices[0].message.content = '{"relevant_skills": ["inspection"]}'
    mock_select.usage.prompt_tokens = 5
    mock_select.usage.completion_tokens = 5
    
    mock_decomp = MagicMock()
    mock_decomp.choices[0].message.content = """
    {
        "reasoning": "Assign one inspection task.",
        "tasks": [
            {
                "task_id": "repair_task",
                "task_type": 0,
                "target": {"kind": 0, "points": [{"x": 1.0, "y": 1.0}], "asset_id": "", "sector_id": ""},
                "constraints": {"require_sensors": ["RGB"]},
                "priority": 100,
                "dependencies": []
            }
        ]
    }
    """
    mock_decomp.usage.prompt_tokens = 10
    mock_decomp.usage.completion_tokens = 10
    mock_completion.side_effect = [mock_select, mock_decomp]
    
    # 4. Submit Mission
    mission_id = "mission_heal"
    orchestrator.submit_mission(MissionInput(mission_id=mission_id, description="fix stuff"))
    
    # 5. Wait for assignment
    timeout = time.time() + 10
    assigned_robot_id = None
    while time.time() < timeout:
        mission = orchestrator.missions.get(mission_id)
        if mission and "repair_task" in mission.tasks:
            task = mission.tasks["repair_task"]
            if task.assigned_robot_id:
                assigned_robot_id = task.assigned_robot_id
                break
        time.sleep(0.5)
    
    assert assigned_robot_id is not None
    print(f"Task assigned to {assigned_robot_id}")
    
    # 6. Kill the assigned robot
    broker.publish("fault_injection", {"robot_id": assigned_robot_id, "fault": "OFFLINE"})
    
    # 7. Wait for self-healing (re-allocation to the other robot)
    # The monitor loop runs every 2 seconds
    timeout = time.time() + 15
    reassigned = False
    while time.time() < timeout:
        mission = orchestrator.missions.get(mission_id)
        task = mission.tasks["repair_task"]
        if task.assigned_robot_id and task.assigned_robot_id != assigned_robot_id:
            reassigned = True
            print(f"Task reassigned to {task.assigned_robot_id}")
            break
        time.sleep(1.0)
        
    assert reassigned is True
    
    uav1.stop()
    uav2.stop()
