import math
import logging
from typing import List, Dict, Optional, Tuple, Any
from ..models.robot import Robot
from ..models.task import Task

logger = logging.getLogger(__name__)

class ResourceAllocator:
    """
    Matches tasks to the best available robots based on capabilities,
    battery, and distance.
    """
    def __init__(self):
        pass

    def allocate(self, tasks: List[Task], robots: List[Robot]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """
        Returns a mapping of task_id -> robot_id and allocation metadata.
        """
        assignments = {}
        metadata = {"attempts": []}
        available_robots = [r for r in robots if r.is_idle()]
        
        # Simple greedy allocation
        # Sort tasks by priority (highest first)
        sorted_tasks = sorted(tasks, key=lambda x: x.priority, reverse=True)
        
        for task in sorted_tasks:
            if not available_robots:
                metadata["attempts"].append({"task_id": task.task_id, "reason": "No idle robots available"})
                continue
                
            best_robot, score, robot_results = self._find_best_robot(task, available_robots)
            if best_robot:
                assignments[task.task_id] = best_robot.robot_id
                available_robots.remove(best_robot)
                metadata["attempts"].append({
                    "task_id": task.task_id, 
                    "assigned_to": best_robot.robot_id,
                    "score": score,
                    "robot_results": robot_results
                })
            else:
                metadata["attempts"].append({
                    "task_id": task.task_id, 
                    "reason": "No capable robots found",
                    "robot_results": robot_results
                })
                
        return assignments, metadata

    def _find_best_robot(self, task: Task, robots: List[Robot]) -> Tuple[Optional[Robot], float, List[Dict[str, Any]]]:
        """
        Scores robots for a specific task and returns detailed results.
        """
        best_robot = None
        best_score = -1.0
        results = []
        
        for robot in robots:
            res = {"robot_id": robot.robot_id}
            
            # 1. Check capability
            if not robot.has_capability(task.spec.task_type):
                res["suited"] = False
                res["reason"] = f"Missing capability {task.spec.task_type}"
                results.append(res)
                continue
                
            # 2. Check battery constraint
            if robot.last_state.battery_pct < task.spec.constraints.min_battery_pct_to_start:
                res["suited"] = False
                res["reason"] = f"Low battery: {robot.last_state.battery_pct}%"
                results.append(res)
                continue
                
            # 3. Check sensor requirements
            required_sensors = [s.upper() for s in task.spec.constraints.require_sensors]
            available_sensors = [s.upper() for s in robot.capabilities.sensors]
            missing_sensors = [s for s in required_sensors if s not in available_sensors]
            
            if missing_sensors:
                res["suited"] = False
                res["reason"] = f"Missing sensors: {missing_sensors}"
                results.append(res)
                continue
                
            # 4. Scoring logic
            dist = self._calculate_dist(task, robot)
            score = robot.last_state.battery_pct / (1.0 + dist)
            
            res["suited"] = True
            res["score"] = score
            res["dist"] = dist
            results.append(res)
            
            if score > best_score:
                best_score = score
                best_robot = robot
                
        return best_robot, best_score, results

    def _calculate_dist(self, task: Task, robot: Robot) -> float:
        """ Calculates distance from robot to task target. """
        # Simplified: Use first point in target list
        if not task.spec.target.points:
            return 0.0
            
        target_point = task.spec.target.points[0]
        dx = target_point.x - robot.last_state.x_m
        dy = target_point.y - robot.last_state.y_m
        return math.sqrt(dx*dx + dy*dy)
