# Developer Guide: Sutradhara Orchestrator

This guide provides a complete workflow for setting up the Sutradhara Orchestrator environment, running simulations, and using the agentic mission system.

---

## 1. Prerequisites
- **Docker & Docker Compose**: Ensure you have the latest version of Docker Desktop (macOS/Windows) or Docker Engine (Linux).
- **Disk Space**: At least 30GB of free space is recommended (PX4 dependencies are large).
- **RAM**: 8GB+ (16GB recommended for running Gazebo and LLMs simultaneously).

## 2. Environment Setup

### Configuration
Copy the example environment file:
```bash
cp .env.docker.example .env
```

### Build Containers
Build the simulation and developer images. This will take 15-30 minutes on the first run as it compiles PX4 and ROS 2 dependencies:
```bash
docker compose build dev sim
```

## 3. Launching the System

You will need three terminal windows to run the full stack.

### Terminal 1: Simulation & Ollama
Start the Ollama service and the simulation environment (Gazebo + PX4):
```bash
# Start Ollama (handles local LLMs)
docker compose up -d ollama ollama-pull

# Start the simulation stack
bash scripts/docker/run_sim_demo.sh
```

### Terminal 2: ROS Bridge (The Orchestrator)
The bridge connects the Python-based AI agent to the ROS 2 physical world:
```bash
docker compose run --rm dev bash -lc '
  source install/setup.bash &&
  cd $ROS2_WS_AI_ROOT/src/sutradhara_orchestrator &&
  python3 -m sutradhara_orchestrator.cli ros-bridge'
```
*Wait for: `[INFO] [sutradhara_orchestrator]: ROS bridge ready. Listening on /orchestrator/mission_input`*

## 4. Sending a Mission

### Terminal 3: Submission
Send a natural language command to the drone:
```bash
docker compose run --rm dev bash -lc '
  source install/setup.bash &&
  ros2 topic pub /orchestrator/mission_input std_msgs/msg/String "{data: '\''Patrol sector 1'\''}" --once'
```

## 5. Monitoring & Auditing

### Viewing Real-time Logic
You can watch the Orchestrator's reasoning and robot status in **Terminal 2**. Look for:
- `TASK_DECOMPOSED`: When the LLM plans the mission.
- `TASK_PROGRESS`: Percent updates from the simulation.

### Accessing Audit Logs
The system records every decision in a structured JSONL format. You can view it from your host machine:
```bash
# View the raw audit trail
cat audit_trail.jsonl

# Use the Replay Tool for a human-readable summary
docker compose run --rm dev bash -lc '
  cd $ROS2_WS_AI_ROOT/src/sutradhara_orchestrator &&
  python3 replay_tool.py --latest-run
'
```

## 6. Troubleshooting
- **No Gazebo window?** Ensure your `DISPLAY` environment variable is set and `xhost` permissions are granted on the host. See `.env.docker.example`.
- **Model not found?** Check Terminal 1 to ensure the `ollama-pull` container finished pulling `qwen3:1.7b`.
- **ModuleNotFoundError?** Always ensure you have `source install/setup.bash` in your commands inside the docker container.
