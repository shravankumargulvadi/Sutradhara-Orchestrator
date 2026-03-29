import json
import logging
import litellm
from typing import List, Dict, Any, Optional, Tuple
from ..skills.loader import SkillLoader
from ..messages.mission_input import MissionInput
from ..messages.task_command import TaskSpec, TaskTarget, TaskConstraints, Point2D
from ..models.task import Task, TaskStatus
from ..orchestrator.token_budget import ModelTokenBudget
from ..utils.config_manager import config
from .sector_catalog import SectorCatalog, SectorDefinition

logger = logging.getLogger(__name__)

class TaskPlanner:
    """
    Decomposes missions into executable task graphs using Gemini and skill context.
    """
    def __init__(
        self,
        skills_dir: Optional[str] = None,
        model: Optional[str] = None,
        sectors_file: Optional[str] = None,
    ):
        self.skills_dir = skills_dir or config.get("discovery.skills_directory", "./skills")
        self.skill_loader = SkillLoader(self.skills_dir)
        self.model = model or config.get("llm.main_model", "gemini/gemini-2.0-flash")
        self.sector_catalog = SectorCatalog(sectors_file or config.get("discovery.sectors_file"))

    def decompose(self, mission: MissionInput, world_state: Dict[str, Any],
                  token_budget: ModelTokenBudget) -> Tuple[List[Task], str]:
        """
        Decomposes a mission into a list of Task objects and returns reasoning.
        """
        deterministic_tasks, deterministic_reasoning = self._fallback_patrol_tasks(mission)
        if deterministic_tasks:
            logger.info("Using deterministic patrol fallback for mission %s", mission.mission_id)
            return deterministic_tasks, deterministic_reasoning

        # 1. Select relevant skills
        selected_skills = self.skill_loader.select_skills(mission.description, token_budget)
        
        # 2. Build the system prompt with skill docs
        skills_context = "\n\n".join([
            f"### Skill: {s.name}\n{s.content}" 
            for s in selected_skills
        ])

        system_prompt = (
            "You are an expert robot mission planner. Decompose the mission into a list of executable tasks.\n"
            "Use these skills for reference:\n"
            f"{skills_context}\n\n"
            "If the mission is a patrol over a named sector or named operational area, prefer a PATROL task "
            "that uses target.kind=3 (SECTOR_ID) and target.sector_id.\n\n"
            "Respond ONLY with a JSON object containing 'tasks' and 'reasoning' keys.\n"
            "Example:\n"
            "{\n"
            "  \"reasoning\": \"The mission requires inspecting a specific coordinate; I will assign an inspection task to the closest UAV.\",\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"task_id\": \"task_1\",\n"
            "      \"task_type\": 0,\n"
            "      \"target\": {\"kind\": 0, \"points\": [{\"x\": 10, \"y\": 10}], \"asset_id\": \"\", \"sector_id\": \"\"},\n"
            "      \"constraints\": {\"require_sensors\": [], \"min_battery_pct_to_start\": 10},\n"
            "      \"priority\": 50,\n"
            "      \"dependencies\": []\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Task Types: 0=INSPECT, 1=VERIFY, 2=REVISIT, 3=PATROL, 4=RETURN_HOME\n"
            "Target Kinds: 0=POINT, 1=REGION, 2=ASSET_ID, 3=SECTOR_ID"
        )

        sector_context = self._build_sector_context()

        user_prompt = (
            f"Mission: {mission.description}\n\n"
            f"Available Robots & State: {json.dumps(world_state, indent=2)}\n\n"
            f"Available Patrol Sectors: {sector_context}\n\n"
            "Decompose this mission into a task graph."
        )

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Track token usage
            token_budget.track(response)

            # Parse tasks
            content = response.choices[0].message.content
            logger.info("Raw planner LLM response: %s", content)
            
            data = json.loads(content)
            reasoning = data.get("reasoning", "No reasoning provided.")
            task_list_raw = data.get("tasks", [])

            if not isinstance(task_list_raw, list):
                logger.warning(
                    "Planner response 'tasks' field is not a list. Type=%s Content=%s",
                    type(task_list_raw),
                    task_list_raw,
                )
                return [], reasoning

            tasks = []
            for t_raw in task_list_raw:
                try:
                    # Map raw JSON to internal Task model
                    target_raw = t_raw.get("target", {})
                    points = [Point2D(x=p['x'], y=p['y'], z=p.get('z', 0.0)) for p in target_raw.get("points", [])]
                    target = TaskTarget(
                        kind=target_raw.get("kind", 0),
                        points=points,
                        asset_id=target_raw.get("asset_id", ""),
                        sector_id=target_raw.get("sector_id", "")
                    )
                    
                    constraints_raw = t_raw.get("constraints", {})
                    constraints = TaskConstraints(
                        require_sensors=constraints_raw.get("require_sensors", []),
                        min_battery_pct_to_start=constraints_raw.get("min_battery_pct_to_start", 0.0)
                    )
                    
                    spec = TaskSpec(
                        task_type=t_raw.get("task_type", 0),
                        target=target,
                        constraints=constraints,
                        success_criteria=[] 
                    )
                    
                    tasks.append(Task(
                        task_id=t_raw.get("task_id"),
                        mission_id=mission.mission_id,
                        spec=spec,
                        priority=t_raw.get("priority", 50),
                        dependencies=t_raw.get("dependencies", [])
                    ))
                except Exception as item_err:
                    logger.error(f"Error parsing task item: {item_err}. Item content: {t_raw}")

            return tasks, reasoning

        except Exception as e:
            logger.error(f"Error in task planning: {e}")
            if 'response' in locals() and hasattr(response, 'choices'):
                logger.error(f"Failed response content: {response.choices[0].message.content}")
            return [], str(e)

    def _build_sector_context(self) -> str:
        if not self.sector_catalog.sectors:
            return "[]"
        return json.dumps(self.sector_catalog.summaries(), indent=2)

    def _fallback_patrol_tasks(self, mission: MissionInput) -> Tuple[List[Task], str]:
        matched_sector = self.sector_catalog.match_patrol_request(mission.description)
        if not matched_sector:
            return [], ""

        task = self._build_sector_patrol_task(mission, matched_sector)
        reasoning = (
            f"Mission explicitly requests patrol behavior for {matched_sector.display_name}; "
            f"using configured sector patrol {matched_sector.sector_id}."
        )
        return [task], reasoning

    @staticmethod
    def _build_sector_patrol_task(mission: MissionInput, sector: SectorDefinition) -> Task:
        target = TaskTarget(
            kind=TaskTarget.SECTOR_ID,
            sector_id=sector.sector_id,
        )
        spec = TaskSpec(
            task_type=TaskSpec.PATROL,
            target=target,
            constraints=TaskConstraints(),
            success_criteria=["SECTOR_PATROL_COMPLETE"],
        )
        return Task(
            task_id=f"patrol_{sector.sector_id}",
            mission_id=mission.mission_id,
            spec=spec,
            priority=80,
            dependencies=[],
        )

    def summarize(self, mission_desc: str, task_results: List[Dict[str, Any]], 
                  token_budget: ModelTokenBudget) -> str:
        """
        Generates a human-readable summary of the mission outcome.
        """
        system_prompt = (
            "You are a robot mission debriefer. Summarize the outcome of the mission for the user.\n"
            "Keep it professional, concise, and informative."
        )

        user_prompt = (
            f"Mission Objective: {mission_desc}\n\n"
            f"Task Results: {json.dumps(task_results, indent=2)}\n\n"
            "Provide a final summary of what was achieved and any issues encountered."
        )

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            token_budget.track(response)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in mission summarization: {e}")
            return "Mission completed, but failed to generate a detailed summary."
