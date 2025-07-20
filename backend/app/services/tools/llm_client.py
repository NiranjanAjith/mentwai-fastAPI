"""
Azure OpenAI client with optimized connection management.
Handles both classification and streaming response generation.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional, List
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionChunk

from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Async client for Azure OpenAI API with optimized connection management.
    Supports both fast classification and streaming response generation.
    """
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        self._connection_pool_size = 20
        self._semaphore = asyncio.Semaphore(self._connection_pool_size)
    
    async def classify_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 200
    ) -> Dict[str, Any]:
        """
        Fast intent classification using GPT-3.5-turbo.
        Optimized for <200ms response times.
        """
        start_time = time.time()
        
        try:
            async with self._semaphore:
                # Construct system prompt for fast classification
                system_prompt = """You are a fast intent classifier for an AI tutoring system.
                Classify the user's intent into one of these categories:
                - "explain": User wants concept explanations
                - "solve": User needs problem solving assistance  
                - "clarify": User requests clarification
                - "example": User wants examples or demonstrations
                
                Respond with ONLY a JSON object: {"intent": "category", "confidence": 0.95}
                Be fast and decisive. No explanations needed."""
                
                # Add context if provided
                user_content = f"User query: {query}"
                if context:
                    subject = context.get("subject_area", "")
                    if subject:
                        user_content += f"\nSubject: {subject}"
                
                # Make fast classification call
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model="gpt-35-turbo",  # Fast model for classification
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        max_tokens=50,  # Keep it minimal for speed
                        temperature=0.1,  # Low temperature for consistent classification
                        timeout=timeout_ms / 1000.0
                    ),
                    timeout=timeout_ms / 1000.0
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                # Parse response
                content = response.choices[0].message.content.strip()
                
                try:
                    import json
                    result = json.loads(content)
                    result["processing_time_ms"] = processing_time
                    return result
                except json.JSONDecodeError:
                    # Fallback classification
                    logger.warning(f"Failed to parse classification response: {content}")
                    return {
                        "intent": "explain",  # Default to explain
                        "confidence": 0.5,
                        "processing_time_ms": processing_time
                    }
        
        except asyncio.TimeoutError:
            logger.warning(f"Classification timeout after {timeout_ms}ms")
            return {
                "intent": "explain",
                "confidence": 0.3,
                "processing_time_ms": timeout_ms,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"Classification error: {e}")
            processing_time = (time.time() - start_time) * 1000
            return {
                "intent": "explain",
                "confidence": 0.1,
                "processing_time_ms": processing_time,
                "error": str(e)
            }
    
    async def generate_streaming_response(
        self,
        query: str,
        context: Dict[str, Any],
        classification: str = "explain"
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming educational response using GPT-4-turbo.
        Yields chunks of text as they're generated.
        """
        
        try:
            async with self._semaphore:
                # Construct educational system prompt based on classification
                system_prompts = {
                    "explain": """You are an expert AI tutor. Provide clear, educational explanations that:
                    - Break down complex concepts into digestible parts
                    - Use analogies and examples when helpful
                    - Adapt to the user's learning level
                    - Encourage understanding over memorization""",
                    
                    "solve": """You are an expert AI tutor. Help solve problems by:
                    - Breaking down the problem step-by-step
                    - Explaining the reasoning behind each step
                    - Teaching the underlying concepts
                    - Encouraging the user to think through the process""",
                    
                    "clarify": """You are an expert AI tutor. Provide clarifications that:
                    - Address the specific confusion or question
                    - Use simple, clear language
                    - Provide concrete examples
                    - Check for understanding""",
                    
                    "example": """You are an expert AI tutor. Provide examples that:
                    - Illustrate the concept clearly
                    - Show practical applications
                    - Include step-by-step explanations
                    - Connect to real-world scenarios"""
                }
                
                system_prompt = system_prompts.get(classification, system_prompts["explain"])
                
                # Add context to user message
                user_content = f"Subject: {context.get('subject_area', 'general')}\n"
                user_content += f"Query: {query}"
                
                # Add user preferences if available
                preferences = context.get('user_preferences', {})
                if preferences:
                    user_content += f"\nUser preferences: {preferences}"
                
                # Create streaming completion
                stream = await self.client.chat.completions.create(
                    model="gpt-4",  # Use GPT-4 for quality educational responses
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=800,  # Reasonable length for educational responses
                    temperature=0.7,  # Some creativity for engaging explanations
                    stream=True
                )
                
                # Yield chunks as they arrive
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Streaming response error: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    async def health_check(self) -> bool:
        """Check if the LLM client is healthy and responsive."""
        try:
            async with self._semaphore:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model="gpt-35-turbo",
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=5
                    ),
                    timeout=5.0
                )
                return response.choices[0].message.content is not None
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False

# Global instance
llm_client = LLMClient()