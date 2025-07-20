"""
Redis caching layer for high-performance context management.
Handles user profiles, session state, and textbook context caching.
"""

import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Redis-based caching service optimized for sub-100ms response times.
    Provides intelligent caching for user context and educational content.
    """
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.pool_size = settings.REDIS_POOL_SIZE
        self.default_ttl = settings.REDIS_DEFAULT_TTL
        self.redis = None
        self._connection_lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established."""
        if self.redis is None:
            async with self._connection_lock:
                if self.redis is None:
                    try:
                        self.redis = await aioredis.create_redis_pool(
                            self.redis_url,
                            encoding="utf-8",
                            maxsize=self.pool_size
                        )
                        # Test connection
                        await self.redis.ping()
                        logger.info("Redis connection established")
                    except Exception as e:
                        logger.error(f"Failed to connect to Redis: {e}")
                        self.redis = None
                        raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user profile from cache.
        Returns None if not found or Redis unavailable.
        """
        try:
            await self._ensure_connection()
            key = f"user_profile:{user_id}"
            
            cached_data = await self.redis.get(key)
            if cached_data:
                profile = json.loads(cached_data)
                # Check if cache is still fresh
                cached_at = profile.get("cached_at", 0)
                if datetime.utcnow().timestamp() - cached_at < self.default_ttl:
                    logger.debug(f"Cache hit for user profile: {user_id}")
                    return profile
            
            logger.debug(f"Cache miss for user profile: {user_id}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get user profile from cache: {e}")
            return None
    
    async def set_user_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """Cache user profile with TTL."""
        try:
            await self._ensure_connection()
            key = f"user_profile:{user_id}"
            
            # Add timestamp
            profile["cached_at"] = datetime.utcnow().timestamp()
            
            await self.redis.setex(
                key,
                self.default_ttl,  # 10 minutes default TTL
                json.dumps(profile)
            )
            logger.debug(f"Cached user profile: {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache user profile: {e}")
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state from cache."""
        try:
            await self._ensure_connection()
            key = f"session_state:{session_id}"
            
            cached_data = await self.redis.get(key)
            if cached_data:
                session = json.loads(cached_data)
                logger.debug(f"Cache hit for session: {session_id}")
                return session
            
            logger.debug(f"Cache miss for session: {session_id}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get session state from cache: {e}")
            return None
    
    async def set_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """Cache session state with extended TTL (2 hours)."""
        try:
            await self._ensure_connection()
            key = f"session_state:{session_id}"
            
            # Add timestamp
            state["cached_at"] = datetime.utcnow().timestamp()
            
            await self.redis.setex(
                key,
                7200,  # 2 hours TTL for sessions
                json.dumps(state, default=str)  # Handle datetime serialization
            )
            logger.debug(f"Cached session state: {session_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache session state: {e}")
            return False
    
    async def get_textbook_context(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve textbook context based on query hash.
        Uses query hash as cache key for fast lookups.
        """
        try:
            await self._ensure_connection()
            
            # Create hash of query for cache key
            query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
            key = f"textbook_context:{query_hash}"
            
            cached_data = await self.redis.get(key)
            if cached_data:
                context = json.loads(cached_data)
                # Check freshness (1 hour TTL for textbook content)
                cached_at = context.get("cached_at", 0)
                if datetime.utcnow().timestamp() - cached_at < 3600:
                    logger.debug(f"Cache hit for textbook context: {query_hash}")
                    return context
            
            logger.debug(f"Cache miss for textbook context: {query_hash}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get textbook context from cache: {e}")
            return None
    
    async def set_textbook_context(self, query: str, context: Dict[str, Any]) -> bool:
        """Cache textbook context with 1 hour TTL."""
        try:
            await self._ensure_connection()
            
            query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
            key = f"textbook_context:{query_hash}"
            
            # Add timestamp
            context["cached_at"] = datetime.utcnow().timestamp()
            
            await self.redis.setex(
                key,
                3600,  # 1 hour TTL for textbook content
                json.dumps(context)
            )
            logger.debug(f"Cached textbook context: {query_hash}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache textbook context: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        try:
            session_state = await self.get_session_state(session_id)
            if session_state:
                session_state["last_activity"] = datetime.utcnow().isoformat()
                return await self.set_session_state(session_id, session_state)
            return False
            
        except Exception as e:
            logger.warning(f"Failed to update session activity: {e}")
            return False
    
    async def increment_conversation_count(self, session_id: str) -> int:
        """Increment conversation count for session."""
        try:
            await self._ensure_connection()
            
            # Try to increment atomically
            count_key = f"session_count:{session_id}"
            count = await self.redis.incr(count_key)
            await self.redis.expire(count_key, 7200)  # 2 hours TTL
            
            return count
            
        except Exception as e:
            logger.warning(f"Failed to increment conversation count: {e}")
            return 1
    
    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self._ensure_connection()
            pong = await self.redis.ping()
            return pong == b'PONG'
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

# Global instance
cache_manager = CacheManager()