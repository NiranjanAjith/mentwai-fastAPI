from typing import List
from app.framework.context import BaseContext
from app.framework.agents import Agent


# --------------------------------------------------------------------------------
#       Workflow Start
# --------------------------------------------------------------------------------


class WorkflowRunner:
    def __init__(self, context: BaseContext):
        """
        Initialize with a session-specific context containing registered agents.
        """
        self.context = context

    def run_sequence(self, agent_keys: List[str], skip: List[str] = None):
        """
        Run agents sequentially, optionally skipping some.

        Args:
            agent_keys (list): List of agent class names in execution order.
            skip (list): Optional list of agent names to skip.
        """
        skip = skip or []

        for agent_key in agent_keys:
            if agent_key in skip:
                continue

            agent: Agent = self.context.get_agent(agent_key)
            if not agent:
                raise ValueError(f"Agent '{agent_key}' not found in context.")

            output = agent.run()
            self.context.add_to_history(role=agent_key, content=output)

    def run_branching(self, conditions: dict[str, bool], branches: dict[str, List[str]]):
        """
        Conditionally run branches of agent sequences based on boolean conditions.

        Args:
            conditions (dict): Condition flags, e.g. {"needs_lab": True}.
            branches (dict): Mapping of condition keys to agent sequences.
        """
        for condition, should_run in conditions.items():
            if should_run and condition in branches:
                self.run_sequence(branches[condition])


# --------------------------------------------------------------------------------
#       Workflow End
# --------------------------------------------------------------------------------
