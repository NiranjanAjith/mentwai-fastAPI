"""
Main orchestration service coordinating parallel execution of Controller and Tutor agents.
Handles streaming response generation while classification runs in background.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models.chat import ChatRequest, ChatChunk, UserContext, ClassificationResult
from app.services.agents.controller import controller_agent
from app.services.agents.tutor import tutor_agent
from app.services.context.minimal_context import minimal_context_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class OrchestrationError(Exception):
    """Custom exception for orchestration errors."""
    pass

class AIOrchestrator:
    """
    Main orchestration service for parallel agent execution.
    Coordinates Controller and Tutor agents for optimal performance.
    """
    
    def __init__(self):
        self.controller = controller_agent
        self.tutor = tutor_agent
        self.context_service = minimal_context_service
        self.max_concurrent_requests = settings.MAX_CONCURRENT_REQUESTS
        self._active_sessions = set()
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
    
    async def process_parallel_streaming(
        self,
        request: ChatRequest
    ) -> AsyncGenerator[ChatChunk, None]:
        """
        Main coordination logic for parallel agent execution.
        Streams response while classification runs in background.
        
        Flow:
        1. Start context retrieval (parallel)
        2. Begin classification (parallel) 
        3. Start streaming response immediately
        4. Yield chunks as they arrive
        5. Include metadata when classification completes
        """
        overall_start_time = time.time()
        session_id = request.session_id
        
        try:
            # Acquire semaphore to limit concurrent requests
            async with self._semaphore:
                self._active_sessions.add(session_id)
                
                # Phase 1: Start parallel context retrieval and classification
                context_task = asyncio.create_task(
                    self._retrieve_context_safely(request)
                )
                
                # Phase 2: Get initial context (fast path)
                try:
                    context = await asyncio.wait_for(context_task, timeout=0.1)
                except asyncio.TimeoutError:
                    # Use minimal context if retrieval is slow
                    logger.debug(f"Using minimal context for session {session_id}")
                    context = UserContext(
                        current_subject=request.subject_area,
                        difficulty_level="intermediate"
                    )
                
                # Phase 3: Start classification in parallel
                classification_task = asyncio.create_task(
                    self._classify_safely(request, context, session_id)
                )
                
                # Phase 4: Generate immediate response preview
                preview_task = asyncio.create_task(
                    self._generate_preview(request, context)
                )
                
                # Phase 5: Start streaming (don't wait for classification)
                streaming_started = False
                classification_result = None
                chunk_count = 0
                
                # Yield immediate metadata
                yield ChatChunk(
                    event="metadata",
                    processing_time=0.0,
                    timestamp=datetime.utcnow()
                )
                
                # Phase 6: Parallel execution - stream response while waiting for classification
                async def stream_with_classification():
                    nonlocal classification_result, streaming_started, chunk_count
                    
                    # Wait for either classification or preview (whichever comes first)
                    done, pending = await asyncio.wait(
                        [classification_task, preview_task],
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=0.4  # 400ms max wait for first response
                    )
                    
                    # Get classification result if available
                    if classification_task in done:
                        try:
                            classification_result = classification_task.result()
                        except Exception as e:
                            logger.warning(f"Classification failed: {e}")
                            classification_result = self._get_fallback_classification(request.query)
                    else:
                        # Cancel classification task if taking too long
                        classification_task.cancel()
                        classification_result = self._get_fallback_classification(request.query)
                    
                    # Yield classification metadata
                    yield ChatChunk(
                        event="metadata",
                        classification=classification_result.intent,
                        processing_time=classification_result.processing_time_ms / 1000,
                        timestamp=datetime.utcnow()
                    )
                    
                    streaming_started = True
                    
                    # Start streaming response
                    async for chunk_text in self.tutor.generate_streaming_response(
                        request.query, context, classification_result, session_id
                    ):
                        chunk_count += 1
                        yield ChatChunk(
                            event="chunk",
                            content=chunk_text,
                            timestamp=datetime.utcnow()
                        )
                        
                        # Small pause every 5 chunks to prevent overwhelming
                        if chunk_count % 5 == 0:
                            await asyncio.sleep(0.005)
                
                # Execute streaming with error handling
                try:
                    async for chunk in stream_with_classification():
                        yield chunk
                
                except Exception as e:
                    logger.error(f"Streaming error for session {session_id}: {e}")
                    yield ChatChunk(
                        event="error",
                        error_message=f"Streaming interrupted: {str(e)[:100]}",
                        timestamp=datetime.utcnow()
                    )
                
                # Phase 7: Final metadata
                total_time = (time.time() - overall_start_time) * 1000
                
                yield ChatChunk(
                    event="complete",
                    total_time=total_time,
                    tokens_generated=chunk_count * 8,  # Rough estimate
                    timestamp=datetime.utcnow()
                )
                
                logger.info(
                    f"Session {session_id} completed: {chunk_count} chunks, "
                    f"{total_time:.1f}ms total, classification: {classification_result.intent if classification_result else 'failed'}"
                )
        
        except Exception as e:
            logger.error(f"Orchestration failed for session {session_id}: {e}")
            yield ChatChunk(
                event="error",
                error_message=f"Service temporarily unavailable: {str(e)[:100]}",
                timestamp=datetime.utcnow()
            )
        
        finally:
            # Cleanup
            self._active_sessions.discard(session_id)
            
            # Cancel any remaining tasks
            for task in [classification_task, preview_task]:
                if not task.done():
                    task.cancel()
    
    async def _retrieve_context_safely(self, request: ChatRequest) -> UserContext:
        """Safely retrieve user context with timeout and fallbacks."""
        try:
            return await asyncio.wait_for(
                self.context_service.get_user_context(
                    user_id=None,  # No user_id in current implementation
                    session_id=request.session_id,
                    subject_area=request.subject_area
                ),
                timeout=settings.CONTEXT_RETRIEVAL_TIMEOUT / 1000.0
            )
        except asyncio.TimeoutError:
            logger.debug("Context retrieval timeout, using defaults")
            return UserContext(
                current_subject=request.subject_area,
                difficulty_level="intermediate",
                learning_preferences=request.user_preferences or {}
            )
        except Exception as e:
            logger.warning(f"Context retrieval error: {e}")
            return UserContext(
                current_subject=request.subject_area,
                difficulty_level="intermediate",
                learning_preferences=request.user_preferences or {}
            )
    
    async def _classify_safely(
        self, 
        request: ChatRequest, 
        context: UserContext, 
        session_id: str
    ) -> ClassificationResult:
        """Safely classify intent with timeout and fallbacks."""
        try:
            return await asyncio.wait_for(
                self.controller.classify_intent(request.query, context, session_id),
                timeout=settings.CLASSIFICATION_TIMEOUT / 1000.0 + 0.1  # Add small buffer
            )
        except asyncio.TimeoutError:
            logger.warning(f"Classification timeout for session {session_id}")
            return self._get_fallback_classification(request.query)
        except Exception as e:
            logger.error(f"Classification error for session {session_id}: {e}")
            return self._get_fallback_classification(request.query)
    
    def _get_fallback_classification(self, query: str) -> ClassificationResult:
        """Generate fallback classification when main classification fails."""
        
        # Simple rule-based classification
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["solve", "calculate", "find", "how do"]):
            intent = "solve"
        elif any(word in query_lower for word in ["example", "show", "demonstrate"]):
            intent = "example"
        elif any(word in query_lower for word in ["what is", "clarify", "confused"]):
            intent = "clarify"
        else:
            intent = "explain"
        
        return ClassificationResult(
            intent=intent,
            confidence=0.4,  # Low confidence for fallback
            processing_time_ms=1.0,
            reasoning="Fallback rule-based classification"
        )
    
    async def _generate_preview(self, request: ChatRequest, context: UserContext) -> str:
        """Generate response preview for immediate feedback."""
        try:
            # Create a dummy classification for preview
            preview_classification = ClassificationResult(
                intent="explain",  # Default for preview
                confidence=0.8,
                processing_time_ms=0
            )
            
            return await self.tutor.generate_response_preview(
                request.query, context, preview_classification
            )
        except Exception as e:
            logger.debug(f"Preview generation failed: {e}")
            return "Let me think about this..."
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get current session information and statistics."""
        
        try:
            session_state = await self.context_service.cache.get_session_state(session_id)
            
            return {
                "session_id": session_id,
                "is_active": session_id in self._active_sessions,
                "conversation_count": len(session_state.get("conversation_history", [])) if session_state else 0,
                "last_activity": session_state.get("last_activity") if session_state else None,
                "last_classification": session_state.get("last_classification") if session_state else None
            }
        except Exception as e:
            logger.warning(f"Failed to get session info: {e}")
            return {
                "session_id": session_id,
                "is_active": False,
                "error": str(e)
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        
        health_checks = await asyncio.gather(
            self.controller.health_check(),
            self.tutor.health_check(),
            self.context_service.health_check(),
            self.context_service.cache.health_check(),
            return_exceptions=True
        )
        
        controller_healthy, tutor_healthy, context_healthy, cache_healthy = health_checks
        
        return {
            "overall_status": "healthy" if all(
                isinstance(check, bool) and check 
                for check in health_checks
            ) else "degraded",
            "components": {
                "controller_agent": controller_healthy if isinstance(controller_healthy, bool) else False,
                "tutor_agent": tutor_healthy if isinstance(tutor_healthy, bool) else False,
                "context_service": context_healthy if isinstance(context_healthy, bool) else False,
                "cache_service": cache_healthy if isinstance(cache_healthy, bool) else False
            },
            "active_sessions": len(self._active_sessions),
            "max_concurrent": self.max_concurrent_requests,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Cleanup resources for a specific session."""
        try:
            self._active_sessions.discard(session_id)
            # Additional cleanup if needed
            logger.debug(f"Cleaned up session: {session_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup session {session_id}: {e}")
            return False

# Global instance
ai_orchestrator = AIOrchestrator()