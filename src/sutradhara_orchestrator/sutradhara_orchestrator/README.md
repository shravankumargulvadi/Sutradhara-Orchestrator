# Sutradhara Orchestrator

Sutradhara Orchestrator is a modular, event-driven agent orchestration system designed for managing heterogeneous robot swarms (UAVs and UGVs). It leverages a multi-LLM pipeline for mission planning, task decomposition, and intelligent skill selection, featuring autonomous self-healing capabilities.

## 🌟 Key Features

- **Multi-LLM Integration:** Orchestrates Gemini (deep reasoning) and local Qwen3 (efficient selection) via LiteLLM.
- **Skill-Based Decomposition:** Uses Anthropic-style modular skills to guide the planning process.
- **Autonomous Self-Healing:** Monitors robot heartbeats and automatically reallocates tasks if a unit goes offline.
- **Centralized Configuration:** Managed via `config.yaml` with support for environment variable expansion.
- **Mission Debriefing:** Automatically generates LLM-powered summaries of mission outcomes (success or failure).
- **Audit Trails:** Deeply structured JSONL logging including planner reasoning, allocation scores, and step-by-step robot progress.

## 🛠 Prerequisites & Tools

Before setting up the project, ensure you have the following tools installed:

1.  **Python 3.13+**: [Download Python](https://www.python.org/downloads/)
2.  **uv**: A high-performance Python package manager.
    *   **Install Command**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    *   **Docs**: [github.com/astral-sh/uv](https://github.com/astral-sh/uv)
3.  **Ollama**: Essential for running local LLMs (Qwen3).
    *   **Install Link**: [ollama.com](https://ollama.com/)
    *   **Manual**: After installing, run `ollama pull qwen3:1.7b`
4.  **Google Gemini API Key** (Optional): Required only if using Google models (e.g., Gemini) for planning. [Google AI Studio](https://aistudio.google.com/).

## 🚀 Environment Setup

1.  **Sync Dependencies**:
    Navigate to the orchestrator source directory and initialize the environment:
    ```bash
    cd src/sutradhara_orchestrator
    uv sync
    ```

2.  **Configure API Keys**:
    The system reads the `GEMINI_API_KEY` for mission planning. Create a `.env` file in the project root:
    ```bash
    echo "GEMINI_API_KEY=your_actual_key_here" > .env
    ```

3.  **Verify Local Models**:
    Ensure the local Ollama server is running, then pull the required model for skill selection:
    ```bash
    ollama pull qwen3:1.7b
    ```

## 🎮 Usage

The orchestration stack is managed through the `cli.py` module.

### 1. Launch the Stack
Start the orchestrator along with simulated UAVs and UGVs. The system will automatically discover robots and their capabilities:
```bash
uv run python -m sutradhara_orchestrator.cli launch --uavs 2 --ugvs 1
```
This command enters an **interactive mode** where you can type missions directly.

### 2. Submit a Mission & Get Results
Once the stack is active, describe your mission in natural language at the prompt. The system will decompose the mission, assign tasks, and provide a final **Mission Result Summary**:
```text
[Sutradhara] > Inspect the solar panels and report any overheating spots.

--- MISSION RESULT ---
Infrastructure inspection of 'solar_panels' was successful. 
- UAV_1 completed 4 waypoints using THERMAL sensors.
- Points (10,10) through (30,30) were scanned.
```

### 3. Visualizing the Audit Trail
The structured logs are recorded in `audit_trail.jsonl`. Use the `replay_tool.py` to see a human-readable, colored timeline of events, including LLM reasoning and robot status:

```bash
uv run replay_tool.py --latest-run --follow
```

### 4. Clear History
If the logs become cluttered, use the CLI to clear the audit history:
```bash
uv run python -m sutradhara_orchestrator.cli clear-logs
```

### 5. Simulation & Fault Injection
You can simulate real-world disturbances to test the system's **Self-Healing** capabilities.

```bash
# Force a robot to go offline (simulates a crash or loss of signal)
uv run python -m sutradhara_orchestrator.cli inject-fault --robot-id uav_1 --fault OFFLINE

# Drain a robot's battery to a critical level (5%)
uv run python -m sutradhara_orchestrator.cli inject-fault --robot-id ugv_1 --fault LOW_BATTERY
```

#### How it works:
- **OFFLINE:** The robot stops broadcasting its heartbeat. The `AgenticAI` monitor thread will detect the timeout and automatically re-allocate its pending tasks.
- **LOW_BATTERY:** The robot stays online but will reject new task assignments.

---

## 🏗 Architecture

- **`AgenticAI`:** Central state machine. Tracks runs with unique IDs and manages the mission lifecycle.
- **`AuditLogger`:** Generates `audit_trail.jsonl`. Captures deep metadata for every system decision.
- **`TaskPlanner`:** Decomposes missions into 3D task graphs (X, Y, Z) using Gemini.
- **`ResourceAllocator`:** Scores robots based on proximity, battery, and matching sensors (Case-insensitive).
- **`WorldStateManager`:** Tracks robot discovery and heartbeat liveness. Robots advertise their **Capability Profiles** (Sensors/Task Types) upon connection.
- **`replay_tool.py`:** Visualizer for the structured audit trail.
