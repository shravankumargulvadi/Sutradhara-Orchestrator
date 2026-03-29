import pytest
from unittest.mock import patch, MagicMock
from sutradhara_orchestrator.orchestrator.task_planner import TaskPlanner
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.messages.task_command import TaskSpec, TaskTarget
from sutradhara_orchestrator.orchestrator.token_budget import ModelTokenBudget

@pytest.fixture
def mock_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    patrol_dir = skills_dir / "patrol"
    patrol_dir.mkdir()
    (patrol_dir / "SKILL.md").write_text("""---
name: patrol
description: patrol skill
---
# Patrol skill
""")
    return str(skills_dir)

@pytest.fixture
def mock_sectors_file(tmp_path):
    sectors_file = tmp_path / "sectors.yaml"
    sectors_file.write_text(
        "sectors:\n"
        "  - sector_id: sector_1\n"
        "    display_name: West Solar Rows\n"
        "    default_patrol_route: patrol_sector_1\n"
        "    assets:\n"
        "      - row_01\n"
        "  - sector_id: sector_3\n"
        "    display_name: Inverter Yard\n"
        "    default_patrol_route: patrol_sector_3\n"
        "    assets:\n"
        "      - inverter_01\n"
    )
    return str(sectors_file)

@patch("sutradhara_orchestrator.skills.loader.SkillLoader.select_skills")
@patch("litellm.completion")
def test_task_decomposition(mock_completion, mock_select_skills, mock_skills_dir, mock_sectors_file):
    planner = TaskPlanner(mock_skills_dir, sectors_file=mock_sectors_file)
    budget = ModelTokenBudget("gemini", 1000)
    mission = MissionInput(mission_id="m1", description="Test mission")
    
    # Mock SkillLoader
    mock_select_skills.return_value = []
    
    # Mock LLM response for decomposition
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = """
    {
        "reasoning": "Inspect the requested point.",
        "tasks": [
            {
                "task_id": "t1",
                "task_type": 0,
                "target": {"kind": 0, "points": [{"x": 1.0, "y": 2.0}], "asset_id": "", "sector_id": ""},
                "constraints": {"require_sensors": ["RGB"]},
                "priority": 100,
                "dependencies": []
            }
        ]
    }
    """
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 30
    mock_completion.return_value = mock_resp
    
    tasks, reasoning = planner.decompose(mission, {}, budget)
    
    assert len(tasks) == 1
    assert tasks[0].task_id == "t1"
    assert tasks[0].spec.task_type == 0
    assert tasks[0].spec.target.points[0].x == 1.0
    assert reasoning == "Inspect the requested point."
    assert budget.used_tokens == 50


@patch("sutradhara_orchestrator.skills.loader.SkillLoader.select_skills")
@patch("litellm.completion")
def test_patrol_sector_fallback_for_explicit_sector(
    mock_completion,
    mock_select_skills,
    mock_skills_dir,
    mock_sectors_file,
):
    planner = TaskPlanner(mock_skills_dir, sectors_file=mock_sectors_file)
    budget = ModelTokenBudget("gemini", 1000)
    mission = MissionInput(mission_id="m_patrol_1", description="Patrol sector 1")

    mock_select_skills.return_value = []

    tasks, reasoning = planner.decompose(mission, {}, budget)

    assert len(tasks) == 1
    assert tasks[0].spec.task_type == TaskSpec.PATROL
    assert tasks[0].spec.target.kind == TaskTarget.SECTOR_ID
    assert tasks[0].spec.target.sector_id == "sector_1"
    assert "sector_1" in reasoning
    mock_completion.assert_not_called()
    assert budget.used_tokens == 0


@patch("sutradhara_orchestrator.skills.loader.SkillLoader.select_skills")
@patch("litellm.completion")
def test_patrol_sector_fallback_for_named_area(
    mock_completion,
    mock_select_skills,
    mock_skills_dir,
    mock_sectors_file,
):
    planner = TaskPlanner(mock_skills_dir, sectors_file=mock_sectors_file)
    budget = ModelTokenBudget("gemini", 1000)
    mission = MissionInput(mission_id="m_patrol_2", description="Patrol the inverter yard")

    mock_select_skills.return_value = []

    tasks, reasoning = planner.decompose(mission, {}, budget)

    assert len(tasks) == 1
    assert tasks[0].spec.task_type == TaskSpec.PATROL
    assert tasks[0].spec.target.kind == TaskTarget.SECTOR_ID
    assert tasks[0].spec.target.sector_id == "sector_3"
    assert "Inverter Yard" in reasoning
    mock_completion.assert_not_called()
