import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
import tiktoken

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage

from app.framework.tools import Tool, ToolNotReadyError
from app.core.config import settings

logger = logging.getLogger(__name__)



# --------------------------------------------------------------------------------
#        ViT Provider Base Class Start
# --------------------------------------------------------------------------------


class ViTProvider(Tool):
    name: str = "ViTProvider"
    description: str = "Base class for all LLM providers"
    version: str = "1.0"
    tags: List[str] = Tool.tags + ["vit", "ai", "image-model"]

    def __init__(self):
        self.client = None
        super().__init__()

    def confirm_setup(self) -> bool:
        """
        Confirm that the ViT provider is configured properly.
        Should validate keys, env vars, or connection.
        """
        if not self.config.get("provider_name"):
            raise ToolNotReadyError("No ViT provider specified in config")
        
        return True

    def run(self) -> Union[str, Any]:
        """
        Calls the ViT with a given prompt. Supports both streaming and non-streaming modes.
        Subclasses must override this method with actual API call logic.
        """
        raise NotImplementedError(f"run() not implemented in base ViTProvider")

    def teardown(self) -> None:
        logger.debug(f"[{self.name}] Tearing down ViT client (noop).")
        self.client = None

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "provider": self.config.get("provider_name", "unknown"),
            "model": self.config.get("model", "default"),
        })
        return status


# --------------------------------------------------------------------------------
#        ViT Provider Base Class End
# --------------------------------------------------------------------------------



# --------------------------------------------------------------------------------
#        Azure AI Foundry Class Start
# --------------------------------------------------------------------------------


class AzureVision(ViTProvider):
    name: str = "AzureVisionProvider"
    description: str = "Vision model provider for Azure AI Inference with Llama3"
    version: str = "1.0"
    tags: list[str] = ViTProvider.tags + ["azure", ]

    def __init__(self):
        self.model = settings.VISION_MODEL # "Llama-3.2-Vision-90B-Instruct"
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

    def convert_messages(self, messages: List[dict], image_base64= None) -> List:
        """
        Convert generic messages into AzureVision-compatible OpenAI format.
        Assumes messages[0] contains the base64 image under key 'image_base64'.
        """
        if not image_base64:
            raise ValueError("Missing 'image_base64' in input messages")
        user_prompt = messages[0].get("text_prompt", "Describe the image in detail.")
        system_prompt = messages[0].get("system", "You are a helpful assistant that analyzes educational images.")

        image_data_url = f"data:image/png;base64,{image_base64}"

        return [
            SystemMessage(content=system_prompt),
            UserMessage(content=[
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ])
        ]

    async def run(self, image_base64, messages: List[dict]) -> AsyncGenerator[Dict, None]:
        if not image_base64:
            yield {
                "error": "Image base64 data is required",
                "tokens": 0
            }
            return
        formatted_messages = self.convert_messages(messages, image_base64=image_base64)
        yield self.non_stream(formatted_messages)

    async def non_stream(self, formatted_messages: List) -> AsyncGenerator[Dict, None]:
        """
        Perform a non-streamed call to the Azure multimodal vision model.
        """
        try:
            response = self.client.complete(
                messages=formatted_messages,
                model=self.model,
                temperature=0.7,
                max_tokens=512,
                stream=False,
            )
            content = response.choices[0].message.content.strip() if response.choices else ""
            total_tokens = await self._log_tokens(formatted_messages, content)

            if content:
                logger.info(f"[AzureVision] Response: {content}")
            else:
                logger.warning("[AzureVision] Empty response")
            yield {
                "content": content,
                "tokens": total_tokens
            }
        except Exception as e:
            logger.error(f"[AzureVision] Error: {e}")
            yield {
                "error": f"Error processing image: {str(e)}",
                "tokens": 0
            }

    async def _log_tokens(self, prompt: List, output: str) -> int:
        try:
            system_text = prompt[0].content
            user_text = prompt[1].content[0]["text"]
            prompt_text = f"{system_text}\n{user_text}"
            tokenizer = tiktoken.get_encoding("cl100k_base")
            input_tokens = tokenizer.encode(prompt_text)
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
vision_client = AzureVision()
