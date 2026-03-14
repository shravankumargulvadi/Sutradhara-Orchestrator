import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from ..utils.config_manager import config

class AuditLogger:
    """
    Handles structured logging of system events for auditing and debugging.
    Runs are tracked with a unique run_id.
    """
    def __init__(self, log_path: str = None):
        if log_path is None:
            self.log_path = config.get("audit.log_file", "audit_trail.jsonl")
        else:
            self.log_path = log_path
            
        self.run_id = str(uuid.uuid4())[:8] # Short unique ID for this execution
        
        self.logger = logging.getLogger("audit_logger")
        self.logger.setLevel(logging.INFO)
        
        # Ensure directory exists
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def start_session(self):
        """Logs the start of a session. Should only be called by the main orchestrator."""
        self.log_event("RUN_START", "SYSTEM", {"run_id": self.run_id})

    def log_event(self, event_type: str, mission_id: str, details: Dict[str, Any]):
        """Logs a single audit event as a JSON line."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "mission_id": mission_id,
            "run_id": self.run_id,
            "details": details
        }
        
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
            
            # Also log to standard logger for visibility
            logging.getLogger(__name__).info(f"Audit event: {event_type} (Run: {self.run_id}) for mission {mission_id}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to log audit event: {e}")

# Global instance
audit_logger = AuditLogger()
