---
name: emergency-response
description: >
  Manages urgent, high-priority tasks requiring immediate robot dispatch.
  Use for critical failures, safety hazards, or time-sensitive events.
  Overrides existing lower-priority tasks and enforces rapid response constraints.
---

# Emergency Response

## Overview
This is the highest priority skill. It handles situations where safety or infrastructure integrity is at risk.

## Decomposition Pattern
1. **Immediate Assessment**: Identify the emergency location and type.
2. **Task Preemption**: Identify robots currently on lower-priority tasks that are best suited for the emergency.
3. **Dispatch**:
   - Issue priority `CANCEL` to current tasks for selected robots.
   - Issue higher priority `ASSIGN` task for the emergency.
4. **Success Criteria**: Usually involves reaching the location and providing a live feed or specific intervention metrics (`FIRST_REPONSE_ESTABLISHED`).

## Guidelines
- Ignore normal efficiency scoring (battery optimization, etc.) in favor of speed.
- Maintain a dedicated communication channel/priority for emergency tasks.

## Examples
- "Gas leak detected in Sector 7" -> Immediate cancel of all local INSPECT tasks; dispatch fastest UAV and UGV to Sector 7.
- "Unauthorized entry at west fence" -> Divert nearest patrol robot to the fence immediately.
