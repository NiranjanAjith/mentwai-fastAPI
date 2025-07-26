import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
import tiktoken

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage

from app.framework.tools import Tool, ToolNotReadyError
from app.core.config import settings

logger = logging.getLogger(__name__)



# --------------------------------------------------------------------------------
#        LLM Provider Base Class Start
# --------------------------------------------------------------------------------


class LLMProvider(Tool):
    name: str = "LLMProvider"
    description: str = "Base class for all LLM providers"
    version: str = "1.0"
    tags: list[str] = Tool.tags + ["llm", "ai", "language-model"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client = None
        super().__init__()

    def confirm_setup(self) -> bool:
        """
        Confirm that the LLM provider is configured properly.
        Should validate keys, env vars, or connection.
        """
        if not self.config.get("language-model"):
            raise ToolNotReadyError("No LLM provider specified in config")
        
        return True

    def run(self) -> Union[str, Any]:
        """
        Calls the LLM with a given prompt. Supports both streaming and non-streaming modes.
        Subclasses must override this method with actual API call logic.
        """
        raise NotImplementedError(f"run() not implemented in base LLMProvider")

    def teardown(self) -> None:
        logger.debug(f"[{self.name}] Tearing down LLM client (noop).")
        self.client = None

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "provider": self.config.get("provider_name", "unknown"),
            "model": self.config.get("model", "default"),
        })
        return status


# --------------------------------------------------------------------------------
#        LLM Provider Base Class End
# --------------------------------------------------------------------------------



# --------------------------------------------------------------------------------
#        Azure AI Foundry Class Start
# --------------------------------------------------------------------------------


class AzureLLM(LLMProvider):
    name: str = "AzureLLMProvider"
    description: str = "LLM provider for Azure AI Inference with Llama3"
    version: str = "1.0"
    tags: list[str] = LLMProvider.tags + ["azure", ]


    def __init__(
        self,
    ):
        self.model = settings.LANGUAGE_MODEL # "Llama-3.3-70B-Instruct"
        self.endpoint = settings.AZURE_ENDPOINT
        self.api_key = settings.AZURE_KEY
        self.client: Optional[ChatCompletionsClient] = None
        super().__init__()

    def confirm_setup(self) -> bool:
        if not self.api_key:
            raise ToolNotReadyError("AZURE_FOUNDRY_API_KEY not set")

        try:
            self.client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            return True
        except Exception as e:
            logger.error(f"[AzureLLMProvider] Initialization failed: {e}")
            return False

    def _convert_messages(self, system_prompt: str, history: List[Dict[str, str]], prompt) -> List:
        messages = [SystemMessage(content=system_prompt)]
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(UserMessage(content=content))
            elif role == "assistant":
                messages.append(AssistantMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
        messages.append(UserMessage(content=prompt))
        return messages

    async def run(
        self,
        prompt: str,
        history: List[Dict[str, str]],
        system_prompt: str = "You are a helpful assistant.",
        stream: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.client:
            raise ToolNotReadyError("Azure LLM client not initialized")

        messages = self._convert_messages(system_prompt, history, prompt)
        logger.info(f"Calling Azure LLM (stream={stream}) with model {self.model}")

        if stream:
            return self._stream_response(messages, prompt, temperature, max_tokens)
        else:
            return self._non_streaming_response(messages, prompt, temperature, max_tokens)

    async def _stream_response(
        self,
        messages: List,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        full_response = ""
        try:
            response = self.client.complete(
                messages=messages,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )

            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        full_response += delta.content
                        yield {
                            "is_end": False,
                            "content": delta.content,
                            "status_code": 6000,
                        }

            total_tokens = await self._log_tokens(prompt, full_response)
            yield {
                "is_end": True,
                "content": "",
                "status_code": 6000,
                "tokens": total_tokens
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "is_end": True,
                "content": "",
                "error": f"Error: {str(e)}",
                "status_code": 6001,
                "tokens": 0
            }

    async def _non_streaming_response(
        self,
        messages: List,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            response = self.client.complete(
                messages=messages,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            content = response.choices[0].message.content if response.choices else ""

            total_tokens = await self._log_tokens(prompt, content)

            yield {
                "is_end": True,
                "content": content,
                "status_code": 6000,
                "tokens": total_tokens
            }

        except Exception as e:
            logger.error(f"Non-streaming error: {e}")
            yield {
                "is_end": True,
                "error": str(e),
                "status_code": 6001,
                "tokens": 0
            }

    async def _log_tokens(self, prompt: str, output: str) -> int:
        try:
            tokenizer = tiktoken.get_encoding("cl100k_base")
            input_tokens = tokenizer.encode(prompt)
            output_tokens = tokenizer.encode(output)
            total_tokens = len(input_tokens) + len(output_tokens)
            logger.info(f"[AzureLLM] Token count: {total_tokens}")
            return total_tokens
        
        except Exception as e:
            logger.error(f"Token logging failed: {e}")
            return 0


# --------------------------------------------------------------------------------
#        Azure AI Foundry Class End
# --------------------------------------------------------------------------------



# Global instance
llm_client = AzureLLM()

