"""
High-performance context retrieval service optimized for <100ms response times.
Provides essential user and educational context while minimizing latency.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.chat import UserContext, SessionInfo
from app.services.context.cache_manager import cache_manager

logger = logging.getLogger(__name__)

class MinimalContextService:
    """
    Streamlined context retrieval service optimized for speed.
    Focuses on essential context only with aggressive caching.
    """
    
    def __init__(self):
        self.cache = cache_manager
        self.context_timeout = 100  # 100ms timeout for context retrieval
    
    async def get_user_context(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        subject_area: str = "general"
    ) -> UserContext:
        """
        Retrieve essential user context with fallbacks for missing data.
        Target: <100ms response time.
        """
        start_time = time.time()
        
        try:
            # Start parallel context retrieval
            tasks = []
            
            # Get user profile if user_id provided
            if user_id:
                tasks.append(self._get_user_profile_with_timeout(user_id))
            else:
                tasks.append(self._get_default_user_profile())
            
            # Get session context if session_id provided
            if session_id:
                tasks.append(self._get_session_context_with_timeout(session_id))
            else:
                tasks.append(self._get_default_session_context())
            
            # Execute in parallel with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.context_timeout / 1000.0
                )
                
                user_profile, session_context = results
                
                # Handle exceptions gracefully
                if isinstance(user_profile, Exception):
                    logger.warning(f"User profile retrieval failed: {user_profile}")
                    user_profile = self._get_default_user_profile_sync()
                
                if isinstance(session_context, Exception):
                    logger.warning(f"Session context retrieval failed: {session_context}")
                    session_context = self._get_default_session_context_sync()
                
            except asyncio.TimeoutError:
                logger.warning(f"Context retrieval timeout ({self.context_timeout}ms)")
                user_profile = self._get_default_user_profile_sync()
                session_context = self._get_default_session_context_sync()
            
            # Build user context
            context = UserContext(
                user_id=user_id,
                current_subject=subject_area or user_profile.get("current_subject", "general"),
                difficulty_level=user_profile.get("difficulty_level", "intermediate"),
                learning_preferences=user_profile.get("preferences", {}),
                session_history=session_context.get("conversation_history", [])
            )
            
            retrieval_time = (time.time() - start_time) * 1000
            logger.debug(f"Context retrieved in {retrieval_time:.1f}ms")
            
            return context
            
        except Exception as e:
            retrieval_time = (time.time() - start_time) * 1000
            logger.error(f"Context retrieval failed after {retrieval_time:.1f}ms: {e}")
            
            # Return minimal fallback context
            return UserContext(
                user_id=user_id,
                current_subject=subject_area,
                difficulty_level="intermediate",
                learning_preferences={},
                session_history=[]
            )
    
    async def _get_user_profile_with_timeout(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with timeout handling."""
        try:
            profile = await asyncio.wait_for(
                self.cache.get_user_profile(user_id),
                timeout=0.05  # 50ms timeout
            )
            
            if profile:
                return profile
            
            # If not in cache, return default and cache it
            default_profile = self._get_default_user_profile_sync()
            # Cache asynchronously without waiting
            asyncio.create_task(
                self.cache.set_user_profile(user_id, default_profile)
            )
            return default_profile
            
        except asyncio.TimeoutError:
            logger.debug(f"User profile cache timeout for {user_id}")
            return self._get_default_user_profile_sync()
    
    async def _get_default_user_profile(self) -> Dict[str, Any]:
        """Get default user profile asynchronously."""
        return self._get_default_user_profile_sync()
    
    def _get_default_user_profile_sync(self) -> Dict[str, Any]:
        """Synchronous default user profile."""
        return {
            "current_subject": "general",
            "difficulty_level": "intermediate",
            "preferences": {
                "explanation_style": "detailed",
                "include_examples": True,
                "step_by_step": True
            }
        }
    
    async def _get_session_context_with_timeout(self, session_id: str) -> Dict[str, Any]:
        """Get session context with timeout handling."""
        try:
            session = await asyncio.wait_for(
                self.cache.get_session_state(session_id),
                timeout=0.05  # 50ms timeout
            )
            
            if session:
                return session
            
            # Create new session context
            default_session = self._get_default_session_context_sync()
            # Cache asynchronously without waiting
            asyncio.create_task(
                self.cache.set_session_state(session_id, default_session)
            )
            return default_session
            
        except asyncio.TimeoutError:
            logger.debug(f"Session context cache timeout for {session_id}")
            return self._get_default_session_context_sync()
    
    async def _get_default_session_context(self) -> Dict[str, Any]:
        """Get default session context asynchronously."""
        return self._get_default_session_context_sync()
    
    def _get_default_session_context_sync(self) -> Dict[str, Any]:
        """Synchronous default session context."""
        return {
            "conversation_history": [],
            "context_summary": "Starting new learning session",
            "last_classification": None,
            "started_at": datetime.utcnow().isoformat()
        }
    
    async def get_relevant_textbook_content(
        self,
        query: str,
        subject_area: str = "general",
        max_snippets: int = 3
    ) -> List[str]:
        """
        Get relevant textbook content snippets.
        Uses vector search with caching for speed.
        Target: <80ms response time.
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key_query = f"{subject_area}:{query}"
            cached_content = await asyncio.wait_for(
                self.cache.get_textbook_context(cache_key_query),
                timeout=0.03  # 30ms cache timeout
            )
            
            if cached_content and cached_content.get("snippets"):
                retrieval_time = (time.time() - start_time) * 1000
                logger.debug(f"Textbook content cache hit in {retrieval_time:.1f}ms")
                return cached_content["snippets"][:max_snippets]
            
            # If not in cache, return mock content for now
            # TODO: Implement actual vector search integration
            mock_snippets = self._get_mock_textbook_snippets(query, subject_area)
            
            # Cache the result asynchronously
            asyncio.create_task(
                self.cache.set_textbook_context(
                    cache_key_query,
                    {"snippets": mock_snippets, "relevance_scores": [0.9, 0.8, 0.7]}
                )
            )
            
            retrieval_time = (time.time() - start_time) * 1000
            logger.debug(f"Textbook content retrieved in {retrieval_time:.1f}ms")
            
            return mock_snippets[:max_snippets]
            
        except Exception as e:
            retrieval_time = (time.time() - start_time) * 1000
            logger.warning(f"Textbook content retrieval failed after {retrieval_time:.1f}ms: {e}")
            return []
    
    def _get_mock_textbook_snippets(self, query: str, subject_area: str) -> List[str]:
        """Generate mock textbook snippets based on subject area."""
        subject_snippets = {
            "calculus": [
                "The derivative of a function measures its instantaneous rate of change.",
                "Integration is the reverse process of differentiation.",
                "The fundamental theorem of calculus connects derivatives and integrals."
            ],
            "biology": [
                "Photosynthesis converts light energy into chemical energy.",
                "Cell division is essential for growth and reproduction.",
                "DNA contains the genetic instructions for all living organisms."
            ],
            "physics": [
                "Newton's laws describe the relationship between forces and motion.",
                "Energy can neither be created nor destroyed, only transformed.",
                "Electromagnetic waves carry energy through space."
            ],
            "general": [
                "Understanding concepts requires breaking them into smaller parts.",
                "Practice and repetition help strengthen learning.",
                "Real-world examples make abstract concepts more concrete."
            ]
        }
        
        return subject_snippets.get(subject_area.lower(), subject_snippets["general"])
    
    async def update_session_context(
        self,
        session_id: str,
        user_query: str,
        classification: str,
        response_preview: str = ""
    ) -> bool:
        """Update session context with new interaction."""
        try:
            session_context = await self.cache.get_session_state(session_id)
            if not session_context:
                session_context = self._get_default_session_context_sync()
            
            # Add to conversation history (keep last 10 interactions)
            history = session_context.get("conversation_history", [])
            history.append({
                "user_query": user_query,
                "classification": classification,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep only last 10 interactions for performance
            if len(history) > 10:
                history = history[-10:]
            
            session_context["conversation_history"] = history
            session_context["last_classification"] = classification
            session_context["last_activity"] = datetime.utcnow().isoformat()
            
            # Update cache asynchronously
            asyncio.create_task(
                self.cache.set_session_state(session_id, session_context)
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to update session context: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if context service is healthy."""
        try:
            # Test basic context retrieval
            start_time = time.time()
            context = await self.get_user_context(subject_area="test")
            retrieval_time = (time.time() - start_time) * 1000
            
            return retrieval_time < 200  # Should be under 200ms
        except Exception as e:
            logger.error(f"Context service health check failed: {e}")
            return False

# Global instance
minimal_context_service = MinimalContextService()