import uuid
import logging
import threading
import time
from enum import Enum
from typing import Dict, List, Optional

from ..pubsub.broker import broker
from ..messages.mission_input import MissionInput
from ..messages.task_command import TaskCommand
from ..messages.task_ack import TaskAck
from ..messages.task_update import TaskUpdate
from ..messages.robot_state import RobotState

from ..models.mission import Mission, MissionStatus
from ..models.task import Task, TaskStatus
from ..models.robot import Robot

from .task_planner import TaskPlanner
from .resource_allocator import ResourceAllocator
from .world_state_manager import WorldStateManager
from .token_budget import MissionTokenBudget
from .audit_logger import audit_logger
from ..utils.config_manager import config

logger = logging.getLogger(__name__)

class AgenticAI:
    """
    Main orchestrator state machine. Handles missions, replanning, and self-healing.
    """
    def __init__(self, skills_dir: Optional[str] = None):
        skills_path = skills_dir or config.get("discovery.skills_directory", "./skills")
        self.world_manager = WorldStateManager()
        self.planner = TaskPlanner(skills_path)
        self.allocator = ResourceAllocator()
        
        self.missions: Dict[str, Mission] = {}
        self.lock = threading.RLock()
        
        # Start monitoring thread
        self.stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Start Audit Session
        audit_logger.start_session()

        # Subscribe to feedback topics
        broker.subscribe("task_ack", self._on_task_ack)
        broker.subscribe("task_update", self._on_task_update)
        broker.subscribe("mission_input", self._on_mission_input)

    def shutdown(self):
        self.stop_event.set()
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

    def _monitor_loop(self):
        """ Periodically checks for robot timeouts and task liveness. """
        while not self.stop_event.is_set():
            time.sleep(2.0)
            self._handle_robot_timeouts()
            
            # Periodically try to allocate pending tasks for active missions
            with self.lock:
                for mission in list(self.missions.values()):
                    if mission.status == MissionStatus.EXECUTING:
                        self._allocate_pending_tasks(mission)

    def _handle_robot_timeouts(self):
        active_ids = [r.robot_id for r in self.world_manager.get_active_robots()]
        
        with self.lock:
            for mission in self.missions.values():
                if mission.status != MissionStatus.EXECUTING:
                    continue
                
                reallocate_needed = False
                for task in mission.tasks.values():
                    if task.status == TaskStatus.ASSIGNED or task.status == TaskStatus.IN_PROGRESS:
                        if task.assigned_robot_id not in active_ids:
                            logger.warning(f"Robot {task.assigned_robot_id} timed out while executing {task.task_id}")
                            audit_logger.log_event("ROBOT_TIMEOUT", mission.mission_id, 
                                                   {"robot_id": task.assigned_robot_id, "task_id": task.task_id})
                            task.status = TaskStatus.PENDING
                            task.assigned_robot_id = None
                            reallocate_needed = True
                
                if reallocate_needed:
                    self._allocate_pending_tasks(mission)

    def _on_mission_input(self, msg_dict: dict):
        mission_input = MissionInput(**msg_dict)
        self.submit_mission(mission_input)

    def submit_mission(self, mission_input: MissionInput):
        """ Entry point for a new mission. """
        with self.lock:
            mission = Mission(
                mission_id=mission_input.mission_id,
                description=mission_input.description,
                status=MissionStatus.PLANNING
            )
            self.missions[mission.mission_id] = mission
            
        audit_logger.log_event("MISSION_RECEIVED", mission.mission_id, 
                               {"description": mission.description})
        
        # Start planning in a thread
        threading.Thread(target=self._run_planning_cycle, args=(mission,), daemon=True).start()

    def _run_planning_cycle(self, mission: Mission):
        """ Decomposes mission and allocates tasks. """
        try:
            # 1. Decompose
            model_name = config.get("llm.main_model", "gemini/gemini-2.0-flash")
            budget = MissionTokenBudget().get_budget(model_name)
            world_summary = self.world_manager.get_world_summary()
            
            mission_input = MissionInput(
                mission_id=mission.mission_id,
                description=mission.description
            )
            
            tasks, reasoning = self.planner.decompose(mission_input, world_summary, budget)
            
            if not tasks:
                self._fail_mission(mission.mission_id, f"No tasks produced by planner. Reasoning: {reasoning}")
                return

            with self.lock:
                mission.tasks = {t.task_id: t for t in tasks}
                mission.status = MissionStatus.EXECUTING

            audit_logger.log_event("TASK_DECOMPOSED", mission.mission_id, 
                                   {
                                       "count": len(tasks), 
                                       "reasoning": reasoning,
                                       "world_state": world_summary,
                                       "tasks": [t.to_dict() for t in tasks]
                                   })
            
            # 2. Allocate
            self._allocate_pending_tasks(mission)

        except Exception as e:
            logger.error(f"Planning cycle failed: {e}")
            self._fail_mission(mission.mission_id, str(e))

    def _allocate_pending_tasks(self, mission: Mission):
        """ Matches pending tasks with available robots. """
        with self.lock:
            pending = mission.get_tasks_by_status(TaskStatus.PENDING)
            # Only robots that are idle
            robots = self.world_manager.get_active_robots()
            
            logger.info(f"Allocating {len(pending)} tasks to {len(robots)} active robots.")
            
            if not pending: return
            
            try:
                assignments, alloc_metadata = self.allocator.allocate(pending, robots)
                logger.info(f"Allocator returned: {assignments} with metadata {alloc_metadata}")
                
                for task_id, robot_id in assignments.items():
                    logger.info(f"Processing assignment: {task_id} -> {robot_id}")
                    task = mission.tasks.get(task_id)
                    robot = next((r for r in robots if r.robot_id == robot_id), None)
                    if not task:
                        logger.error(f"Task {task_id} not found in mission {mission.mission_id}")
                        continue
                        
                    task.assigned_robot_id = robot_id
                    task.status = TaskStatus.ASSIGNED
                    
                    # Send command
                    self._send_command(task, robot_id)
                    
                    audit_logger.log_event("ROBOT_ASSIGNED", mission.mission_id, 
                                           {
                                               "task_id": task_id, 
                                               "robot_id": robot_id,
                                               "task_spec": task.spec.to_dict() if hasattr(task.spec, 'to_dict') else str(task.spec),
                                               "robot_state": robot.last_state.to_dict() if robot and hasattr(robot.last_state, 'to_dict') else {},
                                               "allocation_metadata": alloc_metadata
                                           })
            except Exception as e:
                logger.error(f"Error during task allocation: {e}")

    def _send_command(self, task: Task, robot_id: str):
        cmd = TaskCommand(
            mission_id=task.mission_id,
            task_id=task.task_id,
            command_id=str(uuid.uuid4()),
            robot_id=robot_id,
            type=TaskCommand.ASSIGN,
            priority=task.priority,
            task=task.spec
        )
        broker.publish("task_command", cmd.to_dict())

    def _on_task_ack(self, ack_dict: dict):
        ack = TaskAck(**ack_dict)
        with self.lock:
            mission = self.missions.get(ack.mission_id)
            if not mission: return
            
            task = mission.tasks.get(ack.task_id)
            if not task: return
            
            if ack.decision == TaskAck.REJECTED:
                logger.warning(f"Task {ack.task_id} rejected by {ack.robot_id}: {ack.reject_reason_detail}")
                task.status = TaskStatus.PENDING
                task.assigned_robot_id = None
                # Trigger reallocation
                self._allocate_pending_tasks(mission)
            else:
                audit_logger.log_event("TASK_ACK_RECEIVED", mission.mission_id, 
                                       {
                                           "task_id": task.task_id, 
                                           "robot_id": ack.robot_id,
                                           "task_spec": task.spec.to_dict()
                                       })

    def _on_task_update(self, update_dict: dict):
        update = TaskUpdate(**update_dict)
        with self.lock:
            mission = self.missions.get(update.mission_id)
            if not mission: return
            
            task = mission.tasks.get(update.task_id)
            if not task: return
            
            task.progress_pct = update.progress_pct
            task.status_detail = update.status_detail
            
            # Log intermediate progress for transparency
            audit_logger.log_event("TASK_PROGRESS", mission.mission_id, 
                                   {
                                       "task_id": task.task_id, 
                                       "robot_id": update.robot_id,
                                       "task_type": task.spec.task_type,
                                       "progress": f"{task.progress_pct}%",
                                       "detail": task.status_detail
                                   })

            if update.status == TaskUpdate.STATUS_COMPLETED:
                task.status = TaskStatus.COMPLETED
                audit_logger.log_event("TASK_COMPLETED", mission.mission_id, 
                                       {
                                           "task_id": task.task_id, 
                                           "task_type": task.spec.task_type,
                                           "detail": task.status_detail
                                       })
                
                # Check for mission completion or pending dependent tasks
                if mission.all_tasks_completed():
                    mission.status = MissionStatus.COMPLETED
                    logger.info(f"Mission {mission.mission_id} COMPLETED. Generating summary...")
                    
                    # Generate summary in background
                    threading.Thread(target=self._finalize_mission, args=(mission,), daemon=True).start()
                else:
                    self._allocate_pending_tasks(mission)
            
            elif update.status == TaskUpdate.STATUS_FAILED:
                task.status = TaskStatus.FAILED
                audit_logger.log_event("TASK_FAILED", mission.mission_id, 
                                       {"task_id": task.task_id})
                # Trigger replan - simplified for now: just trigger planning cycle again
                mission.status = MissionStatus.PLANNING
                threading.Thread(target=self._run_planning_cycle, args=(mission,), daemon=True).start()

    def _finalize_mission(self, mission: Mission):
        """Generates the final response for a completed or failed mission."""
        try:
            model_name = config.get("llm.main_model", "gemini/gemini-2.0-flash")
            budget = MissionTokenBudget().get_budget(model_name)
            
            task_results = []
            with self.lock:
                for t in mission.tasks.values():
                    task_results.append({
                        "task_id": t.task_id,
                        "status": t.status.value,
                        "detail": t.status_detail,
                        "robot_id": t.assigned_robot_id
                    })
                mission_status = mission.status.value
                mission_desc = mission.description

            summary = self.planner.summarize(mission_desc, task_results, budget)
            
            with self.lock:
                mission.final_response = summary
            
            event_type = "MISSION_COMPLETED" if mission_status == "COMPLETED" else "MISSION_FAILED"
            audit_logger.log_event(event_type, mission.mission_id, 
                                   {"summary": summary, "status": mission_status})
            
            # Also publish to the broker for live UI/CLI feedback
            broker.publish("mission_result", {
                "mission_id": mission.mission_id,
                "summary": summary,
                "status": mission_status
            })
            
            logger.info(f"Mission {mission.mission_id} finalized with summary ({mission_status}).")
            
        except Exception as e:
            logger.error(f"Failed to finalize mission {mission.mission_id}: {e}")
            audit_logger.log_event("MISSION_COMPLETED", mission.mission_id, 
                                   {"summary": "Mission ended, but summary generation failed."})

    def _fail_mission(self, mission_id: str, reason: str):
        with self.lock:
            mission = self.missions.get(mission_id)
            if mission and mission.status != MissionStatus.FAILED:
                mission.status = MissionStatus.FAILED
                mission.final_response = f"Mission Failed: {reason}"
                logger.warning(f"Failing mission {mission_id}: {reason}")
                # Generate formal summary for the failure
                threading.Thread(target=self._finalize_mission, args=(mission,), daemon=True).start()
