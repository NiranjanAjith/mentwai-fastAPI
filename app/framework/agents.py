from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from app.framework.context import BaseContext


# --------------------------------------------------------------------------------
#       Base Agent Start
# --------------------------------------------------------------------------------


class Agent(ABC):
    name: str = "base_agent"
    description: str = "Abstract base agent"

    def __init__(self, context: BaseContext, name: str = "base_agent"):
        self.name = name
        self.context = context
        self.logger = context.get_logger(self.name)

    def update_context(self, key: str, value: Any):
        self.context.set_state(key, value)

    def get_from_context(self, key: str, default=None):
        return self.context.get_state(key, default)

    def validate_output(self, response: Any) -> bool:
        """
        Can be overridden by agent to enforce custom validation on response.
        """
        return True if response else False

    @abstractmethod
    def run(self, query: Optional[str] = None) -> Any:
        pass


# --------------------------------------------------------------------------------
#       Base Agent End
# --------------------------------------------------------------------------------
