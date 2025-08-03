import json
import regex
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.logging import Logger
logger = Logger(name="JailbreakDetector", log_file="jailbreak")

from app.framework.agents import Agent
from app.services.tools.llm import llm_client
from app.services.tools.prompt import prompt_render



class JailbreakDetector(Agent):
    name: str = "jailbreak_detector"
    description: str = "Screens user input for jailbreak attempts."

    def __init__(self, context):
        super().__init__(context, name=self.name)


    async def run(self, query: Optional[str]) -> Dict[str, Any]:
        try:
            start_time = datetime.now()
            logger.info(f"Jailbreak screening at {start_time}")
            logger.info(f"QUERY: {query}")
            self.context.log["info"].append(f"Jailbreak screening at {start_time}")

            history = self.get_from_context("history", [])[-4:]

            try:
                # Prepare system prompt
                prompt_tool = prompt_render
                system_prompt = prompt_tool.render_from_file(
                    template_path="jailbreak/system.j2"
                )
            except Exception as e:
                logger.error(f"Failed to render system prompt: {e}")
                self.context.log["error"].append(f"(Jailbreak Agent) Failed to render system prompt: {e}")
                raise ValueError(f"(Jailbreak Agent) Failed to render system prompt. Please check your configuration. (Error: {e})")
                
            try:
                user_prompt = prompt_tool.render_from_file(
                    template_path="jailbreak/user.j2",
                    variables={"user_query": query}
                )
            except Exception as e:
                logger.error(f"Failed to render user prompt: {e}")
                self.context.log["error"].append(f"(Jailbreak Agent) Failed to render user prompt: {e}")
                raise ValueError(f"(Jailbreak Agent) Failed to render user prompt. Please check your configuration. (Error: {e})")

            try:
                # Run LLM
                llm_tool = llm_client
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

                match = regex.search(r"\{(?:[^{}]|(?R))*\}", response_text, regex.DOTALL)
                if not match:
                    return self._failure("Malformed response. JSON not found.")

                metadata = json.loads(match.group(0))
                if "query_status" not in metadata:
                    return self._failure("Missing 'query_status' in metadata.")
                
                logger.info(f"Jailbreak Screeng Duration: {start_time - datetime.now()}")

                return metadata
            except Exception as e:
                logger.error(f"LLM processing error: {e}")
                self.context.log["error"].append(f"(Jailbreak Agent) LLM processing error: {e}")
                raise ValueError(f"(Jailbreak Agent) LLM processing error. Please check your configuration. (Error: {e})")

        except Exception as e:
            logger.error("Jailbreak detection error", exc_info=True)
            return self._failure(str(e))


    def _failure(self, message: str) -> Dict[str, Any]:
        return {
            "query_status": "error",
            "reason": message,
            "message": "Unable to determine query safety. Please try again."
        }
