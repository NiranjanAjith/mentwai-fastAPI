"""
Primary chat streaming endpoints for AI tutoring interactions.
Implements parallel agent execution with real-time response streaming.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.models.chat import ChatRequest, ChatChunk, SessionInfo
from app.services.orchestrator import ai_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Server-sent events streaming endpoint for AI tutoring.
    
    Performance Targets:
    - First token: <400ms
    - Complete response: 2-4 seconds
    - Concurrent users: 50+
    
    Request Format:
    {
        "query": "What is the derivative of x^2?",
        "subject_area": "calculus",
        "session_id": "uuid-session-identifier",
        "user_preferences": {
            "explanation_style": "detailed",
            "include_examples": true
        }
    }
    
    Response Format (Server-Sent Events):
    data: {"event": "metadata", "classification": "explain", "processing_time": 0.15}
    data: {"event": "chunk", "content": "The derivative of x² is", "timestamp": "..."}
    data: {"event": "complete", "total_time": 2.45, "tokens_generated": 156}
    """
    
    try:
        # Validate request
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if len(request.query) > 2000:
            raise HTTPException(status_code=400, detail="Query too long (max 2000 characters)")
        
        logger.info(f"Starting stream for session {request.session_id}: {request.query[:50]}...")
        
        # Create streaming generator
        async def generate_sse_stream():
            """Generate Server-Sent Events stream."""
            try:
                async for chunk in ai_orchestrator.process_parallel_streaming(request):
                    # Convert ChatChunk to SSE format
                    data = chunk.model_dump_json()
                    yield f"data: {data}\n\n"
                
                # Send final completion signal
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error_chunk = ChatChunk(
                    event="error",
                    error_message=f"Stream interrupted: {str(e)[:100]}"
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
        
        # Add cleanup task
        background_tasks.add_task(
            ai_orchestrator.cleanup_session, 
            request.session_id
        )
        
        # Return streaming response
        return StreamingResponse(
            generate_sse_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    
    except ValidationError as e:
        logger.warning(f"Request validation error: {e}")
        raise HTTPException(status_code=422, detail="Invalid request format")
    
    except Exception as e:
        logger.error(f"Stream endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/feedback")
async def submit_feedback(feedback_data: Dict[str, Any]):
    """
    User feedback collection endpoint.
    
    Request Format:
    {
        "session_id": "uuid",
        "rating": 5,
        "feedback_text": "Great explanation!",
        "response_helpful": true,
        "suggestions": "Maybe add more examples"
    }
    """
    
    try:
        session_id = feedback_data.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        # Store feedback (implement as needed)
        logger.info(f"Feedback received for session {session_id}: {feedback_data.get('rating', 'N/A')}")
        
        # TODO: Implement feedback storage in database
        
        return {
            "status": "success",
            "message": "Feedback received, thank you!",
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Feedback endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/session/{session_id}")
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """
    Get session information and statistics.
    
    Response Format:
    {
        "session_id": "uuid",
        "is_active": true,
        "conversation_count": 5,
        "last_activity": "2025-01-20T13:49:00Z",
        "last_classification": "explain"
    }
    """
    
    try:
        session_info = await ai_orchestrator.get_session_info(session_id)
        return session_info
    
    except Exception as e:
        logger.error(f"Session info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session info")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for the chat service.
    
    Response Format:
    {
        "status": "healthy",
        "components": {
            "controller_agent": true,
            "tutor_agent": true,
            "context_service": true,
            "cache_service": true
        },
        "active_sessions": 12,
        "max_concurrent": 50,
        "timestamp": "2025-01-20T13:49:00Z"
    }
    """
    
    try:
        health_status = await ai_orchestrator.get_system_health()
        
        # Determine HTTP status based on health
        status_code = 200 if health_status["overall_status"] == "healthy" else 503
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-20T13:49:00Z"
        }

@router.get("/history/{user_id}")
async def get_conversation_history(
    user_id: str,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get conversation history for a user.
    
    Note: This is a placeholder endpoint. Full implementation would require
    user authentication and database storage of conversation history.
    """
    
    try:
        # TODO: Implement actual conversation history retrieval
        # This would typically query a database for user's conversation history
        
        logger.info(f"History requested for user {user_id} (limit: {limit}, offset: {offset})")
        
        # Placeholder response
        return {
            "user_id": user_id,
            "conversations": [],
            "total_count": 0,
            "message": "Conversation history feature not yet implemented"
        }
    
    except Exception as e:
        logger.error(f"History endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation history")

# Additional utility endpoints

@router.post("/session/create")
async def create_session(
    subject_area: Optional[str] = "general",
    user_preferences: Optional[Dict[str, Any]] = None
) -> SessionInfo:
    """
    Create a new chat session.
    
    Response Format:
    {
        "session_id": "uuid",
        "subject_area": "calculus",
        "started_at": "2025-01-20T13:49:00Z",
        "is_active": true,
        "conversation_count": 0
    }
    """
    
    try:
        import uuid
        from datetime import datetime
        
        session_info = SessionInfo(
            session_id=str(uuid.uuid4()),
            subject_area=subject_area or "general"
        )
        
        # Initialize session in cache
        await ai_orchestrator.context_service.cache.set_session_state(
            session_info.session_id,
            {
                "started_at": session_info.started_at.isoformat(),
                "subject_area": session_info.subject_area,
                "conversation_history": [],
                "user_preferences": user_preferences or {}
            }
        )
        
        logger.info(f"Created new session: {session_info.session_id}")
        return session_info
    
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    Cleanup and close a session.
    
    Response Format:
    {
        "status": "success",
        "message": "Session cleaned up successfully",
        "session_id": "uuid"
    }
    """
    
    try:
        success = await ai_orchestrator.cleanup_session(session_id)
        
        if success:
            return {
                "status": "success",
                "message": "Session cleaned up successfully",
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found or already cleaned")
    
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup session")