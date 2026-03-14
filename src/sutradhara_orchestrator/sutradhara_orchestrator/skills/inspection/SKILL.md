---
name: infrastructure-inspection
description: >
  Decomposes infrastructure inspection missions into executable task graphs.
  Use when a mission involves surveying, scanning, or inspecting an area or
  set of assets for anomalies. Handles grid-based area coverage, sensor
  selection (THERMAL, RGB, LIDAR), and UAV/UGV assignment. Produces
  INSPECT tasks with appropriate waypoints and success criteria.
---

# Infrastructure Inspection

## Overview
This skill specializes in surveying large areas or specific infrastructure assets to detect anomalies or collect baseline state data.

## Decomposition Pattern
1. **Identify Target Region**: Extract the target area from mission objectives.
2. **Grid Generation**: For area coverage, divide the region into a grid of waypoint cells. Spacing should be determined by sensor Field of View (FOV) and required resolution.
3. **Task Assignment**:
   - Create one INSPECT task per grid cell or per specific asset (e.g., solar panel row).
   - Require sensors based on mission (e.g., THERMAL for heat leaks, RGB for structural).
   - Prefer UAVs for overhead/large area surveys; UGVs for close-up or ground-level inspection.
4. **Success Criteria**: Define criteria such as `COMPLETE_COVERAGE_COLLECTED`, `THERMAL_MAP_GENERATED`, or `IMAGE_SET_CAPTURED`.

## Guidelines
- Avoid overlapping inspection paths to optimize battery usage.
- Ensure minimum flight altitude safety constraints are communicated if applicable.
- If an anomaly is identified, this skill should trigger a transition to the `anomaly-triage` skill for closer verification.

## Examples
- "Inspect solar farm Block A" -> Break Block A into 10m x 10m cells, assign INSPECT tasks to UAVs with THERMAL sensors.
- "Survey the perimeter fence" -> Generate waypoints along the fence line, assign INSPECT task to UGV with RGB camera.
