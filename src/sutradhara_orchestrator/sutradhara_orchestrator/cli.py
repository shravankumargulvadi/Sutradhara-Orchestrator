import os
import time
import uuid
import json
import click
import logging
import threading
from .orchestrator.agentic_ai import AgenticAI
from .ros_node import main as ros_bridge_main
from .pubsub.broker import broker
from .simulation.robot import SimulatedUAV, SimulatedUGV
from .messages.mission_input import MissionInput

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sutradhara_cli")

@click.group()
def cli():
    """Sutradhara Orchestrator CLI"""
    pass

@cli.command()
@click.option("--uavs", default=1, help="Number of Simulated UAVs")
@click.option("--ugvs", default=1, help="Number of Simulated UGVs")
@click.option("--skills", default="./sutradhara_orchestrator/skills", help="Path to skills directory")
def launch(uavs, ugvs, skills):
    """Launch the orchestrator and simulated robots."""
    logger.info(f"Launching Sutradhara Stack with {uavs} UAVs and {ugvs} UGVs...")
    
    # 1. Start Orchestrator
    orchestrator = AgenticAI(skills_dir=skills)
    
    # 2. Start Robots
    robots = []
    for i in range(uavs):
        r = SimulatedUAV(f"uav_{i+1}")
        r.start()
        robots.append(r)
        
    for i in range(ugvs):
        r = SimulatedUGV(f"ugv_{i+1}")
        r.start()
        robots.append(r)

    logger.info("Stack active. Type a mission description to submit, or 'exit' to quit.")
    
    # Listen for mission results to provide feedback
    def on_mission_result(msg):
        print(f"\n\n{Colors.OKGREEN}{Colors.BOLD}--- MISSION RESULT ---{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{msg.get('summary')}{Colors.ENDC}\n")
        print(f"{Colors.GREY}[Sutradhara] > {Colors.ENDC}", end="", flush=True)

    class Colors:
        OKGREEN = '\033[92m'
        BOLD = '\033[1m'
        ENDC = '\033[0m'
        GREY = '\033[90m'

    broker.subscribe("mission_result", on_mission_result)
    
    # Simple interactive loop for missions
    try:
        while True:
            desc = input("\n[Sutradhara] > ")
            if desc.lower() in ["exit", "quit"]:
                break
            if not desc.strip():
                continue
            
            mission_id = f"mission_{int(time.time())}"
            msg = MissionInput(
                mission_id=mission_id,
                description=desc
            )
            logger.info(f"Submitting mission {mission_id}: {desc}")
            broker.publish("mission_input", msg.to_dict())
            
    except (KeyboardInterrupt, EOFError):
        logger.info("Shutting down...")
    finally:
        for r in robots:
            r.stop()
        orchestrator.shutdown()

@cli.command()
@click.argument("description")
@click.option("--id", default=None, help="Mission ID")
def mission(description, id):
    """Submit a mission to the orchestrator."""
    mission_id = id or f"mission_{int(time.time())}"
    msg = MissionInput(
        mission_id=mission_id,
        description=description
    )
    # Since we are running in-process in 'launch' command, or we could use another process
    # for 'mission' command that connects to the same broker (if we had a persistent broker)
    # For now, this CLI assumes it's publishing to the same broker instance.
    # IN A REAL ROS2 SYSTEM, this would be a separate node publishing to /mission_input.
    logger.info(f"Submitting mission {mission_id}: {description}")
    broker.publish("mission_input", msg.to_dict())

@cli.command()
@click.option("--mission-id", help="Mission ID to filter by")
def audit(mission_id):
    """View the audit trail."""
    log_file = "audit_trail.jsonl"
    if not os.path.exists(log_file):
        click.echo("No audit trail found.")
        return
        
    with open(log_file, "r") as f:
        for line in f:
            entry = json.loads(line)
            if not mission_id or entry.get("mission_id") == mission_id:
                click.echo(f"[{entry['timestamp']}] {entry['event_type']}: {entry['details']}")

@cli.command()
def clear_logs():
    """Clear the audit trail logs."""
    from .utils.config_manager import config
    log_file = config.get("audit.log_file", "audit_trail.jsonl")
    if os.path.exists(log_file):
        os.remove(log_file)
        logger.info(f"Cleared audit logs: {log_file}")
    else:
        logger.info("No audit logs found to clear.")

@cli.command()
@click.option("--robot-id", required=True, help="Robot ID")
@click.option("--fault", required=True, type=click.Choice(["OFFLINE", "LOW_BATTERY", "FAILED"]), help="Fault type")
def inject_fault(robot_id, fault):
    """Inject a fault into a robot (simplified for simulation)."""
    logger.info(f"Injecting fault {fault} into {robot_id}")
    broker.publish("fault_injection", {"robot_id": robot_id, "fault": fault})

@cli.command("ros-bridge")
def ros_bridge():
    """Run the ROS-facing orchestrator bridge node."""
    ros_bridge_main()

if __name__ == "__main__":
    cli()
