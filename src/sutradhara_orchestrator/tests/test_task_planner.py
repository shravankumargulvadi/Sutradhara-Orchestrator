import pytest
from unittest.mock import patch, MagicMock
from sutradhara_orchestrator.orchestrator.task_planner import TaskPlanner
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.orchestrator.token_budget import ModelTokenBudget

@pytest.fixture
def mock_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return str(skills_dir)

@patch("sutradhara_orchestrator.skills.loader.SkillLoader.select_skills")
@patch("litellm.completion")
def test_task_decomposition(mock_completion, mock_select_skills, mock_skills_dir):
    planner = TaskPlanner(mock_skills_dir)
    budget = ModelTokenBudget("gemini", 1000)
    mission = MissionInput(mission_id="m1", description="Test mission")
    
    # Mock SkillLoader
    mock_select_skills.return_value = []
    
    # Mock LLM response for decomposition
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = """
    [
        {
            "task_id": "t1",
            "task_type": 0,
            "target": {"kind": 0, "points": [{"x": 1.0, "y": 2.0}]},
            "constraints": {"require_sensors": ["RGB"]},
            "priority": 100,
            "dependencies": []
        }
    ]
    """
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 30
    mock_completion.return_value = mock_resp
    
    tasks = planner.decompose(mission, {}, budget)
    
    assert len(tasks) == 1
    assert tasks[0].task_id == "t1"
    assert tasks[0].spec.task_type == 0
    assert tasks[0].spec.target.points[0].x == 1.0
    assert budget.used_tokens == 50
