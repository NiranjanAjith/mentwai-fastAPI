from datetime import timezone, datetime
from typing import List
from uuid import UUID

# from sqlmodel import select
from sqlalchemy import select, func
# from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import Logger
logger = Logger(name="Tutor Context")

from app.services.tools.llm import llm_client
from app.framework.context import BaseContext
from app.core.config import settings
from app.services.tools.tables.student import Student, StudentTokenUsage, ensure_student
from app.services.tools.tables.textbook import (
    TextBook,
    Subject,
    EducationalBoard,
    Standard,
    TextBookStandardLink
)
from app.services.tools.tables.chat_history import ChatSession
from app.services.tools.tables.base_table import populate_base_fields



class TutorContext(BaseContext):
    def __init__(self, project_name: str = "tutor"):
        super().__init__(project_name=project_name)

        self.rag_documents: List[str] = []


    async def initialize(self, student_id: UUID, textbook_id: UUID):
        self.student_id = student_id
        self.textbook_id = textbook_id

        try:
            self.student = await self._validate_student(student_id)
        except Exception as e:
            raise ValueError(f"Failed to validate student: (Tutor Context initialize Error: {e})")
        
        try:
            self.textbook = await self._validate_textbook(textbook_id)
        except Exception as e:
            raise ValueError(f"Failed to validate textbook: (Tutor Context initialize Error: {e})")
        
        self.log["success"].append(f"(tutor_context.py) initialized successfully for student {self.student.name} and textbook {self.textbook.name}.")


    async def _validate_student(self, user_id: int):
        today = datetime.now(timezone.utc).date()

        async with settings.get_session() as session:
            try:
                stmt = select(Student).where(Student.id == user_id)
                result = await session.execute(stmt)
                student = result.scalars().first()
                logger.info(f"Student {student.name} found.")
                self.log["success"].append(f"(TutorContext) Student {student.name} found.")
            except Exception as e:
                logger.error(f"Error Retrieving Student Details. ({e})")
                self.log["error"].append(f"Error (_validate_student()): {e}")
                raise ValueError(f"Invalid student ID for Student table. Connection denied. (_validate_student() Error: {e})")

            try:
                stmt = select(StudentTokenUsage).where(
                    StudentTokenUsage.date_added == today,
                    StudentTokenUsage.student_id == student.id
                )
                result = await session.execute(stmt)
                student_token_usage = result.scalars().first()

                if not student_token_usage:
                    student_token_usage = StudentTokenUsage(
                        student_id=student.id,
                        date_added=today
                    )
                    logger.info(f"New StudentTokenUsage created for today.")
                    self.log["success"].append(f"(TutorContext) New StudentTokenUsage created for today.")
                else:
                    logger.info(f"StudentTokenUsage for today found.")
                    self.log["success"].append(f"(TutorContext) Student token usage for today found.")

                    session.add(student_token_usage)
                    await session.commit()
                    await session.refresh(student_token_usage)
                    logger.info(f"StudentTokenUsage refreshed from DB.")
                    self.log["success"].append(f"(TutorContext) StudentTokenUsage committed to DB.")
            except Exception as e:
                logger.error(f"Error Retrieving StudentTokenUsage Details. ({e})")
                self.log["error"].append(f"Error (_validate_student()): {e}")
                raise ValueError(f"Invalid student ID for StudentTokenUsage table. Connection denied. (_validate_student() Error: {e})")

        self.student = student
        self.student_name = student.name
        self.student_total_token_usage = student.total_token_usage
        self.student_token_usage = student_token_usage

        logger.info(f"Student {student.name} initialized successfully with total token usage: {self.student_total_token_usage}.")
        self.log["success"].append(f"(TutorContext) Student {student.name} initialized successfully.")

        return student


    async def _validate_textbook(self, textbook_id: int):
        try:
            async with settings.get_session() as session:
                try:
                    # Get textbook with joined subject and board
                    statement = select(TextBook).where(TextBook.id == textbook_id)
                    result = await session.execute(statement)
                    textbook = result.scalars().first()
                    self.log["success"].append(f"(TutorContext) Textbook {textbook.name} found.")
                    logger.info(f"Textbook {textbook.name} found.")
                except Exception as e:
                    self.log["error"].append(f"Error (_validate_textbook()): {e}")
                    logger.error(f"Error Retrieving Textbook Details. ({e})")
                    raise ValueError(f"Invalid textbook ID for Textbook table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get subject
                    subject_stmt = select(Subject).where(Subject.id == textbook.subject_id)
                    result = await session.execute(subject_stmt)
                    subject = result.scalars().first()
                    self.subject_name = subject.name
                    self.log["success"].append(f"(TutorContext) Subject {subject.name} found.")
                    logger.info(f"Subject {subject.name} found.")
                except Exception as e:
                    self.log["error"].append(f"Error (_validate_textbook()): {e}")
                    logger.error(f"Error Retrieving Subject Details. ({e})")
                    raise ValueError(f"Invalid textbook ID for Subject table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get educational board
                    board_stmt = select(EducationalBoard).where(EducationalBoard.id == textbook.educational_board_id)
                    result = await session.execute(board_stmt)
                    board = result.scalars().first()
                    self.educational_board = board.name
                    self.log["success"].append(f"(TutorContext) Educational board {board.name} found.")
                    logger.info(f"Educational board {board.name} found.")
                except Exception as e:
                    self.log["error"].append(f"Error (_validate_textbook()): {e}")
                    logger.error(f"Error Retrieving Educational Board Details. ({e})")
                    raise ValueError(f"Invalid textbook ID for EducationalBoard table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get first standard (many-to-many)
                    stmt = (
                        select(Standard)
                        .join(TextBookStandardLink, TextBookStandardLink.standard_id == Standard.id)
                        .where(TextBookStandardLink.textbook_id == textbook.id)
                    )
                    result = await session.execute(stmt)
                    standards = result.scalars().all()
                    self.standard = standards[0].name if standards else None
                    self.log["success"].append(f"(TutorContext) Standard {self.standard} found." if self.standard else "No standards found for textbook.")
                    logger.info(f"Starndard {self.standard} found.")
                except Exception as e:
                    self.log["error"].append(f"Error (_validate_textbook()): {e}")
                    logger.error(f"Error Retrieving Standard Details. ({e})")
                    raise ValueError(f"Invalid textbook ID for Standard table. Connection denied. (_validate_textbook() Error: {e})")

            self.textbook = textbook
            self.textbook_code = textbook.code

            logger.info(f"Textbook {textbook.name} initialized successfully with subject {self.subject_name}, board {self.educational_board}, and standard {self.standard}.")

            return textbook

        except Exception as e:
            self.log["error"].append(f"Error validating textbook (_validate_textbook() final): {e}")
            logger.error(f"Error validating textbook. ({e})")
            raise ValueError(f"Invalid textbook ID. Connection denied. (_validate_textbook() Error: {e})")


    async def update_student_token_usage(self, token_count: int):
        self.student_total_token_usage += token_count
        self.student.total_token_usage = self.student_total_token_usage

        self.student_token_usage.token_used += token_count

        try:
            async with settings.get_session() as session:
                session.add(self.student)
                session.add(self.student_token_usage)
                await session.commit()
                await session.refresh(self.student)
                await session.refresh(self.student_token_usage)
                self.log["success"].append(f"(TutorContext) Student token usage updated in DB: {self.student_token_usage.token_used} tokens used today.")
                logger.info(f"Student token usage updated in DB: {self.student_token_usage.token_used} tokens used today.")
        except Exception as e:
            self.log["error"].append(f"Error updating student token usage: {e}")
            logger.error(f"Error updating student token usage in DB. ({e})")
            raise ValueError(f"Failed to update student token usage in DB. (_update_student_token_usage Error: {e})")


    async def create_chat_session(self) -> ChatSession:
        
        async with settings.get_session() as session:
            student_id = await ensure_student(session, self.student_id)

            existing_session = await session.scalar(select(ChatSession).where(ChatSession.file_path == str(self.session_id)))
            if existing_session:
                self.logger.info(f"[CHAT SESSION] Skipped: Session already exists for ID: {self.session_id}")
                return

            chat_session = ChatSession(
                student_id=student_id,
                textbook_id=self.textbook_id,
                title=self.get_history()[0]["content"][:15],
                history=self.get_history()[-1]["content"],
                file_path=str(self.session_id),
            )
            chat_session = await populate_base_fields(chat_session, student_id)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return


    # RAG Documents
    def add_rag_document(self, document: str):
        if not isinstance(document, str):
            raise ValueError("RAG document must be a string.")
        self.rag_documents.append(document)
        logger.info(f"Added document to Context: {document[:50]}... (total: {len(self.rag_documents)})")


    def get_rag_documents(self, limit: int = 0) -> List[str]:
        if limit > 0:
            return self.rag_documents[-limit:]
        return self.rag_documents


    # History
    def add_to_history(self, speaker: str, message: str):
        if speaker not in ["user", "assistant"]:
            raise ValueError("Speaker must be 'user' or 'assistant'.")
        super().add_to_history(role=speaker, content=message)
        
        # Save history to S3 after adding a new entry
        self._save_history_to_s3()

        if len(self.history) > 30:
            self._summarize_history()
            # Save the summarized history to S3 again after summarization
            self._save_history_to_s3()


    def _summarize_history(self):
        summary_prompt = (
            "Please provide a concise summary of this conversation history. "
            "Focus on the main topics discussed and any important conclusions or decisions made."
        )
        messages = self.get_history()
        summary = llm_client.run(
            prompt=summary_prompt,
            history=messages,
            temperature=0.3
        )
        self.history = [{"role": "assistant", "content": f"Summary so far:\n\n'''{summary}'''"}]
        self.logger.info("[HISTORY] Conversation summarized due to excessive length.")


    def clear_conversation_history(self):
        self.history.clear()
        self.logger.info("[HISTORY] Cleared conversation history.")
        # Save empty history to S3
        self._save_history_to_s3()


    def reset_context(self):
        super().reset_context()
        # Save empty history to S3 after reset
        self._save_history_to_s3()


    def _save_history_to_s3(self):
        """Save history to S3 bucket using session_id as the key."""
        try:
            import asyncio
            from app.services.tools.storage import storage_client
            
            # Use session_id as the key
            key = f"history_{self.session_id}.json"
            
            # Run in a separate thread to avoid blocking
            asyncio.create_task(asyncio.to_thread(storage_client.save, key, self.history))
            self.logger.debug(f"[HISTORY] Saving history to S3 with key: {key}")
        except ImportError:
            self.logger.warning("[HISTORY] S3 storage client not available, history not saved")
        except Exception as e:
            self.logger.error(f"[HISTORY] Failed to save history to S3: {e}")


    async def close(self):
        """Context cleanup"""

        if len(self.history)>0:
            await self.create_chat_session()



