from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from app.core.logging import get_logger
logger = get_logger(__name__)

from app.framework.agents import Agent
from app.services.tools.prompt import prompt_render
from app.services.tools.llm import llm_client
from app.services.tools.vector import vector_db
# from app.utils.text import clean_math  # Optional: for math formatting


class TutorAgent(Agent):
    name: str = "tutor"
    description: str = "Answers student questions using contextual knowledge."

    def __init__(self, context):
        super().__init__(context, name=self.name)

    async def run(
        self,
        query: Optional[str] = None,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None] | Dict[str, Any]:
        logger.info(f"[TutorAgent] Started at {datetime.now().time()}")
        logger.info(f"Query: {query}")

        try:
            history = self.context.get_history(limit=4)
            context_chunks = self.context.get_rag_documents(limit=4)
            if not context_chunks:
                retriever = vector_db
                context_chunks = await retriever.run(query=query, top_k=4) ##TODO
            
            # Prepare prompts
            prompt_tool = prompt_render
            system_prompt = prompt_tool.render_from_file("tutor/system.j2", variables={
                "student_name": self.context.student_name,
                "subject_name": self.context.subject_name,
                "standard": self.context.standard,
                "educational_board": self.context.educational_board,
                "current_date": datetime.now().strftime("%B %d, %Y")
            })
            user_prompt = prompt_tool.render_from_file("tutor/user.j2", variables={
                "user_query": query,
                "rag_documents": context_chunks
            })

            llm = llm_client

            if stream:
                response_text = ""
                async for chunk in llm.run(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    history=history,
                    stream=True,
                    temperature=0.7,
                    max_tokens=1024
                ):
                    delta = chunk.get("content", "")
                    if delta:
                        response_text += delta
                        yield {"is_end":False, "type": "chunk", "content": delta}

                # cleaned = clean_math(response_text.strip())
                # yield {"type": "end", "content": response_text}

            else:
                response_text = ""
                async for chunk in llm.run(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    history=history,
                    stream=False,
                    temperature=0.7,
                    max_tokens=1024
                ):
                    response_text += chunk.get("content", "")

                # cleaned = clean_math(response_text.strip())
                yield {
                    "is_end": True,
                    "status": "success",
                    "content": response_text
                }
            
            logger.info(f"[TutorAgent] Finished at {datetime.now().time()}")
            self.context.add_to_history("assistant", response_text)

        except Exception as e:
            logger.error("TutorAgent error", exc_info=True)
            yield {
                "is_end": True,
                "status": "error",
                "message": "Something went wrong while answering the question."
            }
