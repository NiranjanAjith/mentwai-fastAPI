import asyncio
import logging
from uuid import UUID

from app.services.context.tutor_context import TutorContext
from app.services.agents.controller import JailbreakDetector
from app.services.agents.tutor import TutorAgent
from app.services.tools.vector import vector_db
from app.services.tools.image import vision_client

logger = logging.getLogger(__name__)

class TutorOrchestrator:
    def __init__(self, student_id: UUID, textbook_id: UUID, context: TutorContext):
        self.student_id = student_id
        self.textbook_id = textbook_id
        self.context = context
        self.jailbreak_agent = None
        self.tutor_agent = None

    @classmethod
    async def create(cls, student_id: UUID, textbook_id: UUID, session_id: UUID = None):
        response = {}
        try:
            try:
                context = TutorContext()
            except Exception as e:
                logger.error(f"[!] Failed to initialize context: {e}")
                raise ValueError(f"Failed to initialize context. Please check your configuration. (Error: {e})")
            try:
                jailbreak_agent = JailbreakDetector(context)
            except Exception as e:
                logger.error(f"[!] Failed to initialize jailbreak agent: {e}")
                raise ValueError(f"Failed to initialize jailbreak agent. Please check your configuration. (Error: {e})")
            try:
                tutor_agent = TutorAgent(context)
            except Exception as e:
                logger.error(f"[!] Failed to initialize tutor agent: {e}")
                raise ValueError(f"Failed to initialize tutor agent. Please check your configuration. (Error: {e})")
        except Exception as e:
            logger.error(f"[!] Failed to initialize agents: {e}")
            raise ValueError(f"Failed to initialize agents. Please check your configuration. (Error: {e})")
        
        if session_id:
            context.session_id = session_id
            #TODO History loading

        try:
            success = await context.initialize(student_id, textbook_id)
            response.update(success)
            response["Success_Log"] += "Orchestrator context initialized successfully. (orchestrator.py)"
        except Exception as e:
            logger.error(f"[!] Failed to initialize context: {e}")
            raise ValueError(f"Failed to initialize context. Please check student and textbook IDs. (Error: {e})")

        self = cls(student_id, textbook_id, context)
        self.jailbreak_agent = jailbreak_agent
        self.tutor_agent = tutor_agent

        return self, response

    async def run(self, user_message: str, images: list = None):
        full_user_query = user_message
        if images:
            image_tasks = [asyncio.create_task(vision_client.run(image_base64=image)) for image in images]
            image_descriptions = await asyncio.gather(*image_tasks)
            # Combine image descriptions into a single string
            image_description = " ".join(desc.get("text", "") for desc in image_descriptions)
            full_user_query += f" {image_description}"

        # Run jailbreak agent and RAG search in parallel
        jailbreak_task = asyncio.create_task(self.jailbreak_agent.run(full_user_query))
        vector_task = asyncio.create_task(self._fetch_relevant_docs(full_user_query))
        jailbreak_result, _ = await asyncio.gather(jailbreak_task, vector_task)

        full_response = ""
        # Add user message to history
        self.context.add_to_history("user", full_user_query)

        if jailbreak_result.get("query_status") == "unsafe":
            # If jailbreak detected, return warning
            full_response = jailbreak_result.get("message", "Your query was flagged as unsafe.")
            yield full_response
            self.context.add_to_history("assistant", full_response)
            return

        # Run tutor agent with the result
        async for chunk in self.tutor_agent.run(full_user_query):
            response = chunk.get("text", "")
            full_response += response
            yield response

        self.context.add_to_history("assistant", full_response)

    async def _fetch_relevant_docs(self, query: str):
        if not self.context.textbook_code:
            logger.warning("No textbook code found. Skipping RAG query.")
            return []

        # Use vector DB to fetch related textbook chunks
        results = await vector_db.query(
            query=query,
            namespace=self.context.textbook_code,
        )

        for doc in results:
            self.context.add_rag_document(doc["text"])

        logger.info(f"[VECTOR] Retrieved {len(results)} documents.")
