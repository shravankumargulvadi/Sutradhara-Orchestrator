import pytest
import os
from unittest.mock import patch, MagicMock
from sutradhara_orchestrator.skills.loader import SkillLoader
from sutradhara_orchestrator.orchestrator.token_budget import ModelTokenBudget

@pytest.fixture
def mock_skills_dir(tmp_path):
    # Create dummy skill structure
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    
    inspect_dir = skills_dir / "inspection"
    inspect_dir.mkdir()
    (inspect_dir / "SKILL.md").write_text("""---
name: infrastructure-inspection
description: Inspects stuff.
---
# Content""")
    
    patrol_dir = skills_dir / "patrol"
    patrol_dir.mkdir()
    (patrol_dir / "SKILL.md").write_text("""---
name: patrol
description: Patrols stuff.
---
# Content""")
    
    return str(skills_dir)

def test_load_all_skills(mock_skills_dir):
    loader = SkillLoader(mock_skills_dir)
    assert len(loader.skills) == 2
    assert loader.skills[0].name in ["infrastructure-inspection", "patrol"]

@patch("litellm.completion")
def test_select_skills(mock_completion, mock_skills_dir):
    loader = SkillLoader(mock_skills_dir)
    budget = ModelTokenBudget("qwen3", 1000)
    
    # Mock LLM response
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"relevant_skills": ["infrastructure-inspection"]}'
    mock_resp.usage.prompt_tokens = 10
    mock_resp.usage.completion_tokens = 5
    mock_completion.return_value = mock_resp
    
    selected = loader.select_skills("Inspect the solar panels", budget)
    
    assert len(selected) == 1
    assert selected[0].name == "infrastructure-inspection"
    assert budget.used_tokens == 15
