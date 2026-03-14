import time
import pytest
import threading
from unittest.mock import patch, MagicMock

from sutradhara_orchestrator.orchestrator.agentic_ai import AgenticAI
from sutradhara_orchestrator.simulation.robot import SimulatedUAV
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.messages.task_command import Point2D
from sutradhara_orchestrator.models.mission import MissionStatus

@patch("litellm.completion")
def test_full_mission_lifecycle(mock_completion, tmp_path):
    # Setup skills dir
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "inspection").mkdir()
    (skills_dir / "inspection" / "SKILL.md").write_text("---\nname: inspection\ndescription: test\n---\ncontent")
    
    # 1. Start Orchestrator
    orchestrator = AgenticAI(skills_dir=str(skills_dir))
    
    # 2. Start a Robot
    uav = SimulatedUAV("uav_e2e")
    uav.advertise()
    uav.start()
    
    # Wait for discovery
    time.sleep(2.0)
    
    # 3. Mock LLM Responses
    # Mock Skill Selection
    mock_select = MagicMock()
    mock_select.choices[0].message.content = '{"relevant_skills": ["inspection"]}'
    mock_select.usage.prompt_tokens = 5
    mock_select.usage.completion_tokens = 5
    
    # Mock Decomposition
    mock_decomp = MagicMock()
    mock_decomp.choices[0].message.content = """
    [
        {
            "task_id": "task_1",
            "task_type": 0,
            "target": {"kind": 0, "points": [{"x": 10.0, "y": 10.0}]},
            "constraints": {"require_sensors": ["RGB"]},
            "priority": 100,
            "dependencies": []
        }
    ]
    """
    mock_decomp.usage.prompt_tokens = 10
    mock_decomp.usage.completion_tokens = 10
    
    # Cycle the mock results
    mock_completion.side_effect = [mock_select, mock_decomp]
    
    # 4. Submit Mission
    mission_id = "mission_e2e"
    mission_input = MissionInput(
        mission_id=mission_id,
        description="Inspect point 10,10"
    )
    orchestrator.submit_mission(mission_input)
    
    # 5. Wait for and verify transition
    # Loop for up to 20 seconds to allow simulation to finish
    timeout = time.time() + 20
    while time.time() < timeout:
        mission = orchestrator.missions.get(mission_id)
        if mission and mission.status == MissionStatus.COMPLETED:
            break
        time.sleep(1)
        
    assert mission is not None
    assert mission.status == MissionStatus.COMPLETED
    assert len(mission.tasks) == 1
    assert mission.tasks["task_1"].status.value == "COMPLETED"
    
    uav.stop()
