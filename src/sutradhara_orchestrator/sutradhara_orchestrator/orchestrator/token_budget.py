from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging
from ..utils.config_manager import config

logger = logging.getLogger(__name__)

class TokenBudgetExhausted(Exception):
    """Exception raised when an LLM token budget is exceeded."""
    pass

@dataclass
class ModelTokenBudget:
    """
    Budget tracking for a single model (e.g., Gemini or Qwen3).
    """
    model_name: str
    max_tokens: Optional[int] = None
    used_tokens: int = 0
    call_history: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if self.max_tokens is None:
            # Try to find a specific budget for this model in config
            # We look for the base name (e.g., 'gemini' from 'gemini/gemini-2.0-flash')
            base_model = self.model_name.split('/')[0].split(':')[0].lower()
            self.max_tokens = config.get(f"token_budget.models.{base_model}")
            
            if self.max_tokens is None:
                # Fallback to a default per-model budget or mission total
                self.max_tokens = config.get("token_budget.mission_total_max", 50000)
                logger.debug(f"No specific budget for {self.model_name}, using default: {self.max_tokens}")

    def track(self, response: Any) -> None:
        """
        Extracts token usage from a LiteLLM response and updates cumulative total.
        """
        try:
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
        except AttributeError:
            input_tokens = response.get('usage', {}).get('prompt_tokens', 0)
            output_tokens = response.get('usage', {}).get('completion_tokens', 0)

        tokens = input_tokens + output_tokens
        self.used_tokens += tokens
        self.call_history.append({
            "input": input_tokens,
            "output": output_tokens,
            "total": tokens
        })

        if self.used_tokens >= self.max_tokens:
            raise TokenBudgetExhausted(
                f"{self.model_name} budget exhausted: {self.used_tokens}/{self.max_tokens}"
            )

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

class MissionTokenBudget:
    """
    Manages dynamic per-model token budgets for a single mission.
    """
    def __init__(self):
        self.trackers: Dict[str, ModelTokenBudget] = {}

    def get_budget(self, model_name: str) -> ModelTokenBudget:
        """
        Returns the appropriate budget tracker for the given model name.
        Creates one if it doesn't exist.
        """
        if model_name not in self.trackers:
            self.trackers[model_name] = ModelTokenBudget(model_name)
        return self.trackers[model_name]

    @property
    def total_used(self) -> int:
        return sum(t.used_tokens for t in self.trackers.values())
