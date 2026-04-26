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
1. **Select Patrol Sector First**: Choose the named patrol sector that best matches the mission.
   - Prefer sector-based patrol targets over explicit waypoints when the environment already defines sectors.
   - Use `target.kind = 3` (`SECTOR_ID`) and populate `target.sector_id`.
2. **Define Patrol Route**: Establish a series of waypoints or a boundary for the robot to monitor.
2. **Scheduling**: Define the frequency or duration of the patrol (e.g., "every 30 minutes", "continuous until 6 PM").
3. **Task Assignment**:
   - For sector patrols, create PATROL tasks that reference the sector instead of enumerating the route manually.
   - Only use ordered waypoints directly when no configured sector exists.
   - Define behavior at waypoints (e.g., "stop for 5 seconds", "pan camera").
4. **Health Monitoring**: Ensure robots rotate to charging stations to maintain persistent coverage.

## Guidelines
- Use randomization in patrol timing or routes if security is a factor.
- Coordinate multiple robots to ensure overlapping or interleaved coverage of a large area.

## Examples
- "Patrol sector 1" -> Create a PATROL task with `target.kind=SECTOR_ID` and `target.sector_id='sector_1'`.
- "Patrol the inverter yard" -> Map the named area to the configured sector, then create a PATROL task using `SECTOR_ID`.
- "Maintain continuous aerial surveillance of the gate" -> Coordinate two UAVs to swap every 15 minutes for persistent view.
