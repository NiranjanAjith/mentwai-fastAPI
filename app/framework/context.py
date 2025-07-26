import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import logging



# --------------------------------------------------------------------------------
#       Context Module Start
# --------------------------------------------------------------------------------


class BaseContext:
    def __init__(self, project_name: str):
        # Constants
        self.logger = logging.getLogger(f"context.{project_name}")
        self.project_name = project_name
        self.session_id = str(uuid.uuid4())
        self.allowed_tools: Dict[str, Any] = {}
        self.agents: Dict[str, Callable] = {}

        # Variables
        self.user_query = ""
        self.history: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}
        self.route_map: List[Dict[str, Any]] = []

    # History management
    def add_to_history(self, role: str, content: str):
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(entry)
        self.logger.info(f"[HISTORY] [{role.upper()}] {content}")

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.history[-limit:] if limit else list(self.history)

    # Shared state access
    def set_state(self, key: str, value: Any):
        self.state[key] = value
        self.logger.debug(f"[STATE] Set {key} = {value}")

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def clear_state(self):
        self.state.clear()
        self.logger.info("[STATE] Cleared")

    # Routing trace (who handled what)
    def add_route_trace(self, agent_name: str, user_input: str, output: str):
        route_entry = {
            "agent": agent_name,
            "input": user_input,
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.route_map.append(route_entry)
        self.logger.info(f"[ROUTE] {agent_name} handled input: {user_input[:50]}...")

    def get_route_map(self) -> List[Dict[str, Any]]:
        return list(self.route_map)

    # Utility
    def reset_context(self):
        self.history.clear()
        self.state.clear()
        self.route_map.clear()
        self.logger.info("[SYSTEM] Context reset.")

    def summary(self) -> Dict[str, Any]:
        return {
            "project": self.project_name,
            "session_id": self.session_id,
            "history_length": len(self.history),
            "tool_count": len(self.allowed_tools),
            "state_keys": list(self.state.keys()),
            "route_entries": len(self.route_map)
        }


# --------------------------------------------------------------------------------
#       Context Module End
# --------------------------------------------------------------------------------
