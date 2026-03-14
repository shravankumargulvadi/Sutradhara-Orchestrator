"""
Sutradhara Flow Debugger
-----------------------
Use this module to step through the orchestrator's logic in VS Code.

Instructions:
1. Set breakpoints in:
   - AgenticAI.submit_mission
   - AgenticAI._run_planning_cycle
   - TaskPlanner.decompose
   - ResourceAllocator.allocate
   - SimulatedRobot._on_task_command
2. Run this script via the VS Code Debugger.
"""

import time
import logging
import sys
import os

# Ensure we can import the package if running from within src/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sutradhara_orchestrator.orchestrator.agentic_ai import AgenticAI
from sutradhara_orchestrator.simulation.robot import SimulatedUAV
from sutradhara_orchestrator.messages.mission_input import MissionInput
from sutradhara_orchestrator.pubsub.broker import broker

# Configure verbose logging to see all event transitions
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("DebugFlow")

def run_debug_session():
    # 0. Setup Paths
    # We'll use the default skills directory relative to the package
    base_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.join(base_dir, "sutradhara_orchestrator", "skills")
    
    logger.info("--- STARTING DEBUG SESSION ---")
    
    # 1. Initialize the Orchestrator (The "High-Level" Brain)
    # Breakpoint inside AgenticAI.__init__ to see subscription setup
    orchestrator = AgenticAI(skills_dir=skills_dir)
    
    # 2. Setup Simulated Robots (The "Low-Level" Execution)
    # These run in their own background threads
    uav = SimulatedUAV("uav_debug")
    uav.start() 
    
    logger.info("Waiting for robot discovery...")
    time.sleep(2.0) # Wait for heartbeat and capability discovery
    
    # 3. Create a Mission
    mission_id = "debug_mission_1"
    description = "Inspect the northern perimeter for any structural damage."
    mission_input = MissionInput(mission_id=mission_id, description=description)
    
    logger.info(f"Submitting Mission: {mission_id}")
    
    # 4. Submit the Mission
    # BREAKPOINT HERE: Step into submit_mission -> _run_planning_cycle
    orchestrator.submit_mission(mission_input)
    
    # 5. Keep the main thread alive to observe the async flow
    # Observe:
    # - Planning thread (Gemini/Qwen calls)
    # - Assignment event (TaskCommand published)
    # - Robot Ack (TaskAck published)
    # - Progress updates appearing in logs
    # - Monitor thread checking for timeouts
    
    try:
        logger.info("Orchestration loop active. Watch the debug console/step through threads.")
        for _ in range(30): # Run for 30 seconds
            time.sleep(1.0)
            status = orchestrator.missions.get(mission_id)
            if status:
                logger.info(f"Current Mission Status: {status.status.value}")
    except KeyboardInterrupt:
        logger.info("Debug session interrupted.")
    finally:
        uav.stop()
        logger.info("--- DEBUG SESSION COMPLETE ---")

if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set or provide a warning
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY not found in environment. Planning might fail if not using mocks.")
    
    run_debug_session()
