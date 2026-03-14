---
name: patrol
description: >
  Sets up and manages periodic sweeps or persistent monitoring of specific areas.
  Use for security, environmental monitoring, or regular status updates
  where robots follow a repeating path or logic.
---

# Patrol

## Overview
The patrol skill is designed for persistent presence and regular data collection over time.

## Decomposition Pattern
1. **Define Patrol Route**: Establish a series of waypoints or a boundary for the robot to monitor.
2. **Scheduling**: Define the frequency or duration of the patrol (e.g., "every 30 minutes", "continuous until 6 PM").
3. **Task Assignment**:
   - Create PATROL tasks with a list of ordered waypoints.
   - Define behavior at waypoints (e.g., "stop for 5 seconds", "pan camera").
4. **Health Monitoring**: Ensure robots rotate to charging stations to maintain persistent coverage.

## Guidelines
- Use randomization in patrol timing or routes if security is a factor.
- Coordinate multiple robots to ensure overlapping or interleaved coverage of a large area.

## Examples
- "Patrol the north parking lot every hour" -> Generate circular route, assign PATROL task to UGV 1.
- "Maintain continuous aerial surveillance of the gate" -> Coordinate two UAVs to swap every 15 minutes for persistent view.
