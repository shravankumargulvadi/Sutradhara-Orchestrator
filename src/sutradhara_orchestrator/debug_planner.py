import json
import logging
import os
import litellm
from sutradhara_orchestrator.orchestrator.task_planner import TaskPlanner
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.orchestrator.token_budget import MissionTokenBudget

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("DebugPlanner")

def test_planner():
    # Use the same skills dir as the package
    base_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.join(base_dir, "sutradhara_orchestrator", "skills")
    
    planner = TaskPlanner(skills_dir=skills_dir)
    budget = MissionTokenBudget().get_budget(planner.model)
    
    mission = MissionInput(
        mission_id="test_id",
        description="Inspect the solar panels and report any overheating spots."
    )
    
    world_state = {
        "count": 1,
        "robots": [
            {
                "robot_id": "uav_1",
                "platform": 0,
                "idle": True,
                "active_task": None
            }
        ]
    }
    
    print(f"Using model: {planner.model}")
    tasks = planner.decompose(mission, world_state, budget)
    
    print(f"Produced {len(tasks)} tasks.")
    for t in tasks:
        print(f" - {t.task_id}: {t.spec.task_type}")

if __name__ == "__main__":
    test_planner()
