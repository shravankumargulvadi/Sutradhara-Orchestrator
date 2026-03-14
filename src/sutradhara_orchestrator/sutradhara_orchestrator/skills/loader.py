import os
import yaml
import json
import logging
import litellm
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from ..orchestrator.token_budget import ModelTokenBudget
from ..utils.config_manager import config

logger = logging.getLogger(__name__)

@dataclass
class Skill:
    name: str
    description: str
    content: str
    path: str

class SkillLoader:
    """
    Loads Anthropic-style skills and uses a lightweight LLM
    to select relevant skills based on mission description.
    """
    def __init__(self, skills_dir: Optional[str] = None, selector_model: Optional[str] = None):
        self.skills_dir = skills_dir or config.get("discovery.skills_directory", "./skills")
        self.selector_model = selector_model or config.get("llm.skill_model", "ollama/qwen3:1.7b")
        self.skills: List[Skill] = self._load_all_skills()

    def _load_all_skills(self) -> List[Skill]:
        skills = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} does not exist.")
            return skills

        for skill_folder in os.listdir(self.skills_dir):
            folder_path = os.path.join(self.skills_dir, skill_folder)
            if not os.path.isdir(folder_path):
                continue

            skill_file = os.path.join(folder_path, "SKILL.md")
            if not os.path.exists(skill_file):
                continue

            try:
                with open(skill_file, "r") as f:
                    raw_content = f.read()
                
                # Parse YAML frontmatter
                if raw_content.startswith("---"):
                    parts = raw_content.split("---", 2)
                    if len(parts) >= 3:
                        metadata = yaml.safe_load(parts[1])
                        name = metadata.get("name", skill_folder)
                        description = metadata.get("description", "")
                        content = parts[2].strip()
                        
                        skills.append(Skill(
                            name=name,
                            description=description,
                            content=content,
                            path=skill_file
                        ))
            except Exception as e:
                logger.error(f"Error loading skill from {skill_file}: {e}")

        logger.info(f"Loaded {len(skills)} skills from {self.skills_dir}")
        return skills

    def select_skills(self, mission_description: str, token_budget: ModelTokenBudget) -> List[Skill]:
        """
        Uses a lightweight LLM to reason over skill descriptions
        and select relevant ones.
        """
        if not self.skills:
            return []

        skill_summaries = [
            {"name": s.name, "description": s.description}
            for s in self.skills
        ]

        system_prompt = (
            "You are a robot mission orchestrator. Given a mission and a list of skills, "
            "identify relevant skills.\n\n"
            "Respond ONLY with a JSON object like this:\n"
            "{\"relevant_skills\": [\"skill_name_1\", \"skill_name_2\"]}"
        )

        user_prompt = f"Mission: {mission_description}\n\nAvailable Skills:\n{json.dumps(skill_summaries)}"

        try:
            response = litellm.completion(
                model=self.selector_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Track token usage
            token_budget.track(response)

            # Parse selection
            content = response.choices[0].message.content
            selection_data = json.loads(content)
            selected_names = selection_data.get("relevant_skills", [])
            
            return [s for s in self.skills if s.name in selected_names]

        except Exception as e:
            logger.error(f"Error selecting skills with LLM: {e}")
            return []
