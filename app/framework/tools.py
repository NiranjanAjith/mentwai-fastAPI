from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from abc import ABC, abstractmethod
from app.core.logging import Logger



# --------------------------------------------------------------------------------
#       Logger Start
# --------------------------------------------------------------------------------


logger = Logger(name="BaseTool", log_file="Tool")


# --------------------------------------------------------------------------------
#       Logger End
# --------------------------------------------------------------------------------



# --------------------------------------------------------------------------------
#       Errors Start
# --------------------------------------------------------------------------------


class ToolNotReadyError(Exception):
    pass

class ToolImplementationError(NotImplementedError):
    pass


# --------------------------------------------------------------------------------
#       Errors End
# --------------------------------------------------------------------------------



# --------------------------------------------------------------------------------
#       Base Tool Start
# --------------------------------------------------------------------------------


class Tool(ABC):
    """
    Base class for all external tools in the framework.
    Every tool must:
    - implement confirm_setup()
    - implement run()
    Optionally, tools may:
    - override teardown()
    - override get_status()
    """

    name: str = "UnnamedTool"  # Should be overridden by child classes
    description: str = "No description provided"
    version: str = "1.0"
    tags: list[str] = []

    def __init__(self):
        self.tool_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now(timezone.utc)
        self.is_ready: bool = False

        logger.debug(f"[{self.name}] Initializing tool...")
        try:
            self.is_ready = self.confirm_setup()
        except Exception as e:
            logger.error(f"[{self.name}] Setup failed: {e}")
            raise ToolNotReadyError(f"Tool '{self.name}' failed to initialize: {e}")

        if not self.is_ready:
            raise ToolNotReadyError(f"Tool '{self.name}' is not ready after setup check.")

        logger.info(f"[{self.name}] Initialized and ready.")

    @abstractmethod
    def confirm_setup(self) -> bool:
        """
        Checks and returns True if the tool is configured correctly.
        Should validate auth, connections, file paths, etc.
        Must raise ToolNotReadyError or return False if setup fails.
        """
        raise ToolImplementationError(f"{self.__class__.__name__} must implement confirm_setup()")

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """
        Main interface to use the tool.
        Arguments depend on tool type.
        """
        raise ToolImplementationError(f"{self.__class__.__name__} must implement run()")

    def teardown(self) -> None:
        """
        Optional. Clean up resources, close connections etc.
        """
        logger.debug(f"[{self.name}] Teardown called. No-op by default.")

    def get_status(self) -> Dict[str, Any]:
        """
        Optional. Returns status info for debugging / health-check.
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "ready": self.is_ready,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "tags": self.tags,
        }

    def __repr__(self):
        return f"<Tool {self.name} v{self.version} (ready={self.is_ready})>"


# --------------------------------------------------------------------------------
#       Base Tool End
# --------------------------------------------------------------------------------



# --------------------------------------------------------------------------------
#       Decorator Start
# --------------------------------------------------------------------------------


from app.core.config import settings
GLOBAL_TOOL_REGISTRY: Dict[str, type[Tool]] = getattr(settings, "GLOBAL_TOOL_REGISTRY", {})

def register_tool(tool_cls):
    if not issubclass(tool_cls, Tool):
        raise TypeError(f"{tool_cls.__name__} is not a subclass of Tool")

    if tool_cls.name in GLOBAL_TOOL_REGISTRY:
        logger.info(f"Tool with name '{tool_cls.name}' already registered")
        return tool_cls

    GLOBAL_TOOL_REGISTRY[tool_cls.name] = tool_cls
    return tool_cls


# --------------------------------------------------------------------------------
#       Decorator End
# --------------------------------------------------------------------------------
