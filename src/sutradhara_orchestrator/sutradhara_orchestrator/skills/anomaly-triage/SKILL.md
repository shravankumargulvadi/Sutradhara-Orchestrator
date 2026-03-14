---
name: anomaly-triage
description: >
  Handles the verification and prioritization of detected anomalies.
  Use when a robot reports an anomaly during an inspection or when 
  a specific point of interest requires closer examination. Matches 
  anomalies to the best available robot for verification (VERIFY tasks).
---

# Anomaly Triage

## Overview
This skill manages the transition from general discovery to specific verification. It ensures that potential issues are confirmed and prioritized.

## Decomposition Pattern
1. **Anomaly Analysis**: Evaluate incoming anomaly reports (location, type, preliminary confidence).
2. **Prioritization**: Assign priority (0-100) based on perceived severity (e.g., "fire" = 100, "rusty bolt" = 10).
3. **Verification Task**:
   - Create a VERIFY task at the anomaly's coordinates.
   - Require higher precision sensors if available (e.g., zoom lens, gas sensor).
   - Prefer robots already nearby or those with specific specialized capabilities.
4. **Conclusion**: Task is successful when `ANOMALY_CONFIRMED` or `ANOMALY_DISMISSED` is reported with high confidence.

## Guidelines
- Maintain a history of dismissed anomalies to prevent redundant verification.
- Escalation: If an anomaly is confirmed as critical, trigger immediate `emergency-response`.

## Examples
- "Potential hot spot detected at point X" -> Assign VERIFY task at point X to closest UAV with zoom camera.
- "Verify structural crack on Bridge Pillar 4" -> Assign VERIFY task to UGV with high-res macro camera.
