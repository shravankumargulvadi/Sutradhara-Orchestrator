"""
Sutradhara Audit Replay Tool
----------------------------
Visualizes the audit_trail.jsonl file as a human-readable timeline.
Supports session segmentation using 'run_id' and 'mission_id'.
"""

import json
import time
import os
import click
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    GREY = '\033[90m'

def format_event(event: dict, last_state: dict) -> str:
    ts = event.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S.%f")[:-3]
    except:
        time_str = ts
        
    etype = event.get("event_type", "UNKNOWN")
    mid = event.get("mission_id", "N/A")
    rid = event.get("run_id", "legacy")
    details = event.get("details", {})
    
    output = []
    
    # 1. Session Separation
    if rid != last_state.get("run_id") and last_state.get("run_id") is not None:
        output.append(f"\n{Colors.GREY}{'='*20} NEW SESSION: {rid} {'='*20}{Colors.ENDC}\n")
    
    # 2. Mission Separation (subtle)
    if mid != last_state.get("mission_id") and mid != "SYSTEM" and last_state.get("mission_id") is not None:
        output.append(f"{Colors.GREY}{'-'*10} Mission: {mid} {'-'*10}{Colors.ENDC}")

    color = Colors.ENDC
    prefix = " • "
    summary = ""
    
    TASK_TYPES = {0: "INSPECT", 1: "VERIFY", 2: "REVISIT", 3: "PATROL", 4: "RETURN_HOME"}

    if "RUN_START" in etype:
        color = Colors.BOLD + Colors.OKBLUE
        prefix = " 🚀 "
        summary = f"ORCHESTRATOR STARTED (Run ID: {rid})"
    elif "MISSION_RECEIVED" in etype:
        color = Colors.HEADER
        prefix = " 📥 "
        summary = f"Mission Start: {details.get('description', '')}"
    elif "TASK_DECOMPOSED" in etype:
        color = Colors.OKBLUE
        prefix = " 📋 "
        reasoning = details.get('reasoning', '')
        world_state = details.get('world_state', {})
        summary = f"Planner Decomposed {details.get('count')} tasks\n"
        summary += f"    {Colors.GREY}Reasoning: {reasoning}{Colors.ENDC}\n"
        for t in details.get('tasks', []):
            spec = t.get('spec', {})
            t_type = TASK_TYPES.get(spec.get('task_type'), f"UNKNOWN({spec.get('task_type')})")
            target = spec.get('target', {})
            points = target.get('points', [])
            pt_str = f"({points[0]['x']}, {points[0]['y']})" if points else "N/A"
            summary += f"    {Colors.GREY}- {t.get('task_id')}: {Colors.BOLD}{t_type}{Colors.ENDC}{Colors.GREY} at {pt_str}{Colors.ENDC}\n"
        summary += f"    {Colors.GREY}World State: {len(world_state.get('robots', []))} active robots{Colors.ENDC}"
    elif "ROBOT_ASSIGNED" in etype:
        color = Colors.OKGREEN
        prefix = " 🤖 "
        score = details.get('allocation_metadata', {}).get('attempts', [{}])[0].get('score', 'N/A')
        spec = details.get('task_spec', {})
        t_type = TASK_TYPES.get(spec.get('task_type'), "TASK")
        sensors = spec.get('constraints', {}).get('require_sensors', [])
        sensor_str = f" [Sensors: {', '.join(sensors)}]" if sensors else ""
        summary = f"Assignment: {details.get('task_id')} ({t_type}){sensor_str} -> {details.get('robot_id')} (Score: {score})"
    elif "TASK_ACK_RECEIVED" in etype:
        color = Colors.BOLD
        prefix = " ✅ "
        summary = f"Robot {details.get('robot_id')} accepted {details.get('task_id')}"
    elif "TASK_PROGRESS" in etype:
        color = Colors.GREY
        prefix = " ⚙️  "
        t_type = TASK_TYPES.get(details.get('task_type'), "TASK")
        summary = f"[{details.get('robot_id')}] {t_type} - {details.get('progress')} - {details.get('detail')}"
    elif "TASK_COMPLETED" in etype:
        color = Colors.OKGREEN
        prefix = " ⭐ "
        t_type = TASK_TYPES.get(details.get('task_type'), "TASK")
        summary = f"Task {details.get('task_id')} ({t_type}) COMPLETED ({details.get('detail', '')})"
    elif "ROBOT_TIMEOUT" in etype:
        color = Colors.FAIL
        prefix = " ⚠️  "
        summary = f"TIMEOUT: Robot {details.get('robot_id')} for {details.get('task_id')}"
    elif "MISSION_COMPLETED" in etype:
        color = Colors.OKGREEN + Colors.BOLD
        prefix = " 🏁 "
        summary = f"MISSION SUCCESSFUL\n"
        if details.get('summary'):
            summary += f"    {Colors.OKGREEN}{details.get('summary')}{Colors.ENDC}"
    elif "MISSION_FAILED" in etype:
        color = Colors.FAIL + Colors.BOLD
        prefix = " ❌ "
        summary = f"MISSION FAILED\n"
        if details.get('summary'):
            summary += f"    {Colors.FAIL}{details.get('summary')}{Colors.ENDC}"
        elif details.get('reason'):
            summary += f"    {Colors.FAIL}Reason: {details.get('reason')}{Colors.ENDC}"
    else:
        summary = str(details)

    event_line = f"{Colors.GREY}{time_str}{Colors.ENDC} {color}[{etype:^18}]{Colors.ENDC}{prefix}{summary}"
    output.append(event_line)
    
    # Update state
    last_state["run_id"] = rid
    if mid != "SYSTEM":
        last_state["mission_id"] = mid
        
    return "\n".join(output)

@click.command()
@click.option("--file", default="audit_trail.jsonl", help="Path to audit log file")
@click.option("--follow", is_flag=True, help="Follow the file for new events")
@click.option("--latest-run", is_flag=True, help="Only show the most recent run")
def replay(file, follow, latest_run):
    """Replays the Sutradhara audit logs as a visual timeline."""
    if not os.path.exists(file):
        print(f"Error: {file} not found.")
        return

    print(f"\n{Colors.HEADER}{Colors.BOLD}SUTRADHARA EVENT TIMELINE{Colors.ENDC}")
    print(f"{Colors.OKBLUE}Source: {file}{Colors.ENDC}\n" + "="*60)

    last_state = {"run_id": None, "mission_id": None}
    
    events = []
    if latest_run:
        # Find latest run id first
        latest_rid = None
        with open(file, 'r') as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    latest_rid = ev.get("run_id")
                except: pass
        
        with open(file, 'r') as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    if ev.get("run_id") == latest_rid:
                        print(format_event(ev, last_state))
                except: pass
    else:
        with open(file, 'r') as f:
            for line in f:
                try:
                    ev = json.loads(line.strip())
                    print(format_event(ev, last_state))
                except: pass

    if follow:
        print(f"\n{Colors.WARNING}Watching for new events... (Ctrl+C to stop){Colors.ENDC}\n")
        with open(file, 'r') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                try:
                    ev = json.loads(line.strip())
                    print(format_event(ev, last_state))
                except:
                    pass

if __name__ == "__main__":
    replay()
