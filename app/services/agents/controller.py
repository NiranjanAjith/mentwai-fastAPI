import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

from app.framework.agents import Agent


class JailbreakDetector(Agent):
    name: str = "jailbreak_detector"
    description: str = "Screens user input for jailbreak attempts."

    def __init__(self, context):
        super().__init__(context, name=self.name)

    async def run(self, query: Optional[str]) -> Dict[str, Any]:
        try:
            self.logger.info(f"Jailbreak screening at {datetime.now().time()}")
            self.logger.info(f"QUERY: {query}")

            history = self.get_from_context("history", [])[-4:]

            # Prepare system prompt
            prompt_tool = self.get_tool("prompt")
            system_prompt = prompt_tool.render_from_file(
                template_path="jailbreak/system.j2"
            )
            user_prompt = prompt_tool.render_from_file(
                template_path="jailbreak/user.j2",
                variables={"user_query": query}
            )

            llm_tool = self.get_tool("llm")

            # Run LLM
            response_text = ""
            async for chunk in llm_tool.run(
                prompt=user_prompt,
                history=history,
                system_prompt=system_prompt,
                stream=False,
                temperature=0,
                max_tokens=1024
            ):
                response_text += chunk.get("content", "")

            match = re.search(r"\{(?:[^{}]|(?R))*\}", response_text, re.DOTALL)
            if not match:
                return self._failure("Malformed response. JSON not found.")

            metadata = json.loads(match.group(0))
            if "query_status" not in metadata:
                return self._failure("Missing 'query_status' in metadata.")

            return metadata

        except Exception as e:
            self.logger.error("Jailbreak detection error", exc_info=True)
            return self._failure(str(e))

    def _failure(self, message: str) -> Dict[str, Any]:
        return {
            "query_status": "error",
            "reason": message,
            "message": "Unable to determine query safety. Please try again."
        }
