import pytest
from dataclasses import dataclass
from sutradhara_orchestrator.orchestrator.token_budget import MissionTokenBudget, TokenBudgetExhausted

@dataclass
class MockUsage:
    prompt_tokens: int
    completion_tokens: int

@dataclass
class MockResponse:
    usage: MockUsage

def test_token_tracking():
    mission_budget = MissionTokenBudget(gemini_max=100, qwen_max=50)
    gemini_budget = mission_budget.get_budget("gemini")
    
    # Track a call
    resp = MockResponse(MockUsage(20, 30))
    gemini_budget.track(resp)
    
    assert gemini_budget.used_tokens == 50
    assert gemini_budget.remaining == 50

def test_token_exhaustion():
    mission_budget = MissionTokenBudget(gemini_max=100)
    gemini_budget = mission_budget.get_budget("gemini")
    
    # Exact limit
    resp1 = MockResponse(MockUsage(50, 50))
    with pytest.raises(TokenBudgetExhausted):
        gemini_budget.track(resp1)

def test_model_routing():
    mb = MissionTokenBudget()
    assert mb.get_budget("gemini-2.0-flash").model_name == "gemini"
    assert mb.get_budget("ollama/qwen3").model_name == "qwen3"
