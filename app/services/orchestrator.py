import asyncio
from uuid import UUID

from app.core.logging import get_logger, Logger
logger = Logger(name="Tutor Orchestrator", log_file="tutor_orchestration") # get_logger(__name__)

from app.services.context.tutor_context import TutorContext
from app.services.agents.controller import JailbreakDetector
from app.services.agents.tutor import TutorAgent
from app.services.tools.vector import vector_db
from app.services.tools.image import vision_client
from app.services.tools.storage import storage_client



# --------------------------------------------------------------------------------
#        Tutor Orchestrator Start
# --------------------------------------------------------------------------------



class TutorOrchestrator:
    def __init__(self,
        student_id: UUID,
        textbook_id: UUID,
        context: TutorContext,
        jailbreak_agent: JailbreakDetector,
        tutor_agent: TutorAgent
    ):
        """ Initialize the orchestrator with student and textbook IDs, context, and agents."""

        self.student_id = student_id
        self.textbook_id = textbook_id
        self.context = context
        self.jailbreak_agent = jailbreak_agent
        self.tutor_agent = tutor_agent


    @classmethod
    async def create(cls,
        student_id: UUID,
        textbook_id: UUID,
        session_id: UUID = None
    ):
        """ Factory method to create a new TutorOrchestrator instance with initialized context and agents."""

        try:
            try:
                context = TutorContext()
            except Exception as e:
                logger.error(f"(TutorOrchestrator) Failed to initialize context: {e}")
                raise ValueError(f"(TutorOrchestrator) Failed to initialize context. Please check your configuration. (Error: {e})")
            try:
                jailbreak_agent = JailbreakDetector(context)
                logger.info("(TutorOrchestrator) Jailbreak agent initialized successfully.")
            except Exception as e:
                context.log["error"].append(f"(TutorOrchestrator) Failed to initialize jailbreak agent: {e}")
                logger.error(f"(TutorOrchestrator) Failed to initialize jailbreak agent: {e}")
                raise ValueError(f"Failed to initialize jailbreak agent. Please check your configuration. (Error: {e})")
            try:
                tutor_agent = TutorAgent(context)
                context.log["success"].append("(TutorOrchestrator) Tutor agent initialized successfully.")
            except Exception as e:
                context.log["error"].append(f"(TutorOrchestrator) Failed to initialize tutor agent: {e}")
                logger.error(f"(TutorOrchestrator) Failed to initialize tutor agent: {e}")
                raise ValueError(f"(TutorOrchestrator) Failed to initialize tutor agent. Please check your configuration. (Error: {e})")
        except Exception as e:
            context.log["error"].append(f"(TutorOrchestrator) Failed to initialize agents: {e}")
            logger.error(f"(TutorOrchestrator) Failed to initialize agents: {e}")
            raise ValueError(f"(TutorOrchestrator) Failed to initialize agents. Please check your configuration. (Error: {e})")
        
        if session_id:
            context.session_id = session_id
            # Load history from S3 if session_id is provided
            try:
                history_data = await asyncio.to_thread(storage_client.load, f"history_{session_id}")
                if history_data and isinstance(history_data, list):
                    context.history = history_data
                    context.log["success"].append(f"Loaded {len(history_data)} history entries from S3 for session {session_id}")
                    logger.info(f"[+] Loaded history for session {session_id} from S3")
            except Exception as e:
                context.log["error"].append(f"Failed to load history from S3: {e}")
                logger.error(f"[!] Failed to load history from S3: {e}")

        try:
            await context.initialize(student_id, textbook_id)
            context.log["success"].append("Orchestrator context initialized successfully. (orchestrator.py)")
        except Exception as e:
            context.log["error"].append(f"Failed to initialize context: {e}")
            logger.error(f"[!] Failed to initialize context: {e}")
            raise ValueError(f"Failed to initialize context. Please check student and textbook IDs. (Error: {e})")

        self = cls(student_id, textbook_id, context, jailbreak_agent, tutor_agent)

        return self, context.log


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
            response = chunk.get("content", "")
            full_response += response
            yield response


    async def _fetch_relevant_docs(self, query: str):
        if not self.context.textbook_code:
            logger.warning("No textbook code found. Skipping RAG query.")
            return []

        # Use vector DB to fetch related textbook chunks
        results = await vector_db.run(
            query=query,
            namespace=self.context.textbook_code,
        )

        for doc in results:
            self.context.add_rag_document(doc if isinstance(doc, str) else doc.get("text", ""))

        logger.info(f"[VECTOR] Retrieved {len(results)} documents.")



# --------------------------------------------------------------------------------
#        Tutor Orchestrator End
# --------------------------------------------------------------------------------
