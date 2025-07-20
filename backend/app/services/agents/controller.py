"""
Fast intent classification agent optimized for <200ms response times.
Determines user intent and routes to appropriate response strategies.
"""

import logging
import time
from typing import Dict, Any, Optional

from app.models.chat import ClassificationResult, UserContext
from app.services.tools.llm_client import llm_client
from app.core.config import settings

logger = logging.getLogger(__name__)

class ControllerAgent:
    """
    Fast intent classification agent for routing user queries.
    Uses GPT-3.5-turbo for speed with minimal token limits.
    """
    
    def __init__(self):
        self.llm_client = llm_client
        self.classification_timeout = settings.CLASSIFICATION_TIMEOUT
        self.max_retries = 2
    
    async def classify_intent(
        self,
        query: str,
        context: UserContext,
        session_id: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify user intent with <200ms target response time.
        
        Classifications:
        - "explain": Concept explanations and definitions
        - "solve": Problem solving assistance
        - "clarify": Clarification requests and questions
        - "example": Example requests and demonstrations
        """
        start_time = time.time()
        
        try:
            # Prepare context for classification
            classification_context = {
                "subject_area": context.current_subject,
                "difficulty_level": context.difficulty_level,
                "session_id": session_id
            }
            
            # Add recent classification context if available
            if context.session_history:
                recent_interactions = context.session_history[-3:]  # Last 3 interactions
                classification_context["recent_patterns"] = [
                    interaction.get("classification") 
                    for interaction in recent_interactions 
                    if interaction.get("classification")
                ]
            
            # Attempt classification with retries
            for attempt in range(self.max_retries + 1):
                try:
                    result = await self.llm_client.classify_intent(
                        query=query,
                        context=classification_context,
                        timeout_ms=self.classification_timeout
                    )
                    
                    processing_time = (time.time() - start_time) * 1000
                    
                    # Validate classification result
                    intent = result.get("intent", "explain")
                    confidence = result.get("confidence", 0.5)
                    
                    # Ensure intent is one of the valid options
                    valid_intents = ["explain", "solve", "clarify", "example"]
                    if intent not in valid_intents:
                        logger.warning(f"Invalid intent '{intent}', defaulting to 'explain'")
                        intent = "explain"
                        confidence = max(0.3, confidence * 0.7)  # Reduce confidence
                    
                    # Create classification result
                    classification = ClassificationResult(
                        intent=intent,
                        confidence=min(1.0, max(0.0, confidence)),
                        processing_time_ms=processing_time,
                        reasoning=self._get_intent_reasoning(intent, query)
                    )
                    
                    logger.info(
                        f"Classification: {intent} (confidence: {confidence:.2f}, "
                        f"time: {processing_time:.1f}ms, attempt: {attempt + 1})"
                    )
                    
                    return classification
                    
                except Exception as e:
                    if attempt < self.max_retries:
                        logger.warning(f"Classification attempt {attempt + 1} failed: {e}, retrying...")
                        continue
                    else:
                        raise e
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Classification failed after {processing_time:.1f}ms: {e}")
            
            # Return fallback classification
            return ClassificationResult(
                intent=self._fallback_classification(query),
                confidence=0.3,
                processing_time_ms=processing_time,
                reasoning="Fallback classification due to service error"
            )
    
    def _fallback_classification(self, query: str) -> str:
        """
        Simple rule-based fallback classification when LLM fails.
        Analyzes query text for common patterns.
        """
        query_lower = query.lower()
        
        # Problem solving keywords
        solve_keywords = ["solve", "calculate", "compute", "find", "how do i", "steps", "answer"]
        if any(keyword in query_lower for keyword in solve_keywords):
            return "solve"
        
        # Example keywords
        example_keywords = ["example", "show me", "demonstrate", "sample", "instance"]
        if any(keyword in query_lower for keyword in example_keywords):
            return "example"
        
        # Clarification keywords
        clarify_keywords = ["what is", "what does", "clarify", "confused", "don't understand"]
        if any(keyword in query_lower for keyword in clarify_keywords):
            return "clarify"
        
        # Default to explain for everything else
        return "explain"
    
    def _get_intent_reasoning(self, intent: str, query: str) -> str:
        """Generate reasoning explanation for the classification."""
        reasoning_map = {
            "explain": f"Query requests explanation of concepts or topics: '{query[:50]}...'",
            "solve": f"Query asks for problem-solving assistance: '{query[:50]}...'",
            "clarify": f"Query seeks clarification or understanding: '{query[:50]}...'",
            "example": f"Query requests examples or demonstrations: '{query[:50]}...'"
        }
        
        return reasoning_map.get(intent, f"Default classification for query: '{query[:50]}...'")
    
    async def get_routing_strategy(self, classification: ClassificationResult) -> Dict[str, Any]:
        """
        Get routing strategy based on classification result.
        Provides guidance for the tutor agent.
        """
        
        strategies = {
            "explain": {
                "approach": "educational_explanation",
                "focus": "concept_breakdown",
                "style": "step_by_step",
                "include_examples": True,
                "tone": "instructional"
            },
            "solve": {
                "approach": "problem_solving",
                "focus": "solution_steps",
                "style": "guided_discovery",
                "include_examples": True,
                "tone": "collaborative"
            },
            "clarify": {
                "approach": "clarification",
                "focus": "addressing_confusion",
                "style": "simple_language",
                "include_examples": False,
                "tone": "supportive"
            },
            "example": {
                "approach": "demonstration",
                "focus": "practical_examples",
                "style": "show_and_tell",
                "include_examples": True,
                "tone": "illustrative"
            }
        }
        
        strategy = strategies.get(classification.intent, strategies["explain"])
        
        # Adjust strategy based on confidence
        if classification.confidence < 0.6:
            strategy["hedge_language"] = True
            strategy["ask_for_clarification"] = True
        
        return strategy
    
    async def health_check(self) -> bool:
        """Check if controller agent is healthy and responsive."""
        try:
            test_context = UserContext(
                current_subject="test",
                difficulty_level="intermediate"
            )
            
            result = await self.classify_intent(
                "What is test?",
                test_context
            )
            
            return (
                result.processing_time_ms < (self.classification_timeout * 2) and
                result.intent in ["explain", "solve", "clarify", "example"]
            )
            
        except Exception as e:
            logger.error(f"Controller agent health check failed: {e}")
            return False

# Global instance
controller_agent = ControllerAgent()