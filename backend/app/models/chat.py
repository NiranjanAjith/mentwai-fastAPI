"""
Pydantic models for chat API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import uuid

class ChatRequest(BaseModel):
    """Request model for chat streaming endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's question or request")
    subject_area: Optional[str] = Field("general", description="Subject area like calculus, biology, etc.")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Session identifier")
    user_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User learning preferences")

class ChatChunk(BaseModel):
    """Individual chunk in streaming response."""
    event: Literal["metadata", "chunk", "complete", "error"]
    content: Optional[str] = None
    classification: Optional[str] = None
    processing_time: Optional[float] = None
    total_time: Optional[float] = None
    tokens_generated: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    user_id: Optional[str] = None
    subject_area: str = "general"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    conversation_count: int = 0
    is_active: bool = True

class UserContext(BaseModel):
    """User context for personalized responses."""
    user_id: Optional[str] = None
    current_subject: str = "general"
    difficulty_level: str = "intermediate"
    learning_preferences: Dict[str, Any] = Field(default_factory=dict)
    session_history: List[Dict[str, Any]] = Field(default_factory=list)

class ClassificationResult(BaseModel):
    """Result from controller agent classification."""
    intent: Literal["explain", "solve", "clarify", "example"]
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: float
    reasoning: Optional[str] = None