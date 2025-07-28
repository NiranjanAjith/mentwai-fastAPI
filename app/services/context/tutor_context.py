from datetime import timezone, datetime
from typing import List
from uuid import UUID

from sqlmodel import select

from app.services.tools.tables.student import Student, StudentTokenUsage
from app.services.tools.tables.textbook import (
    TextBook,
    Subject,
    EducationalBoard,
    Standard
)
from app.services.tools.llm import llm_client
from app.framework.context import BaseContext
from app.core.config import settings



class TutorContext(BaseContext):
    def __init__(self, project_name: str = "tutor"):
        super().__init__(project_name=project_name)

        self.rag_documents: List[str] = []

    async def initialize(self, student_id: UUID, textbook_id: UUID):
        self.student_id = student_id
        response = {}
        try:
            self.student, success = await self._validate_student(student_id)
            response.update(success)
        except Exception as e:
            raise ValueError(f"Failed to validate student: (Tutor Context initialize Error: {e})")
        
        try:
            self.textbook, success = await self._validate_textbook(textbook_id)
            response.update(success)
        except Exception as e:
            raise ValueError(f"Failed to validate textbook: (Tutor Context initialize Error: {e})")
        
        response["Success_Log"] += "TutorContext initialized successfully. (tutorcontext.py)"
        return response

    async def _validate_student(self, user_id: int):
        today = datetime.now(timezone.utc).date()
        response = {"Success_Log": ""}

        async with settings.get_session() as session:
            try:
                stmt = select(Student).where(Student.id == user_id)
                result = await session.execute(stmt)
                student = result.scalars().first()
                response["Success_Log"] += f"Student {student.name} found."
            except Exception as e:
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
                    response["Success_Log"] += f"New StudentTokenUsage created for today."
                else:
                    response["Success_Log"] += f"Student token usage for today found."

                    session.add(student_token_usage)
                    await session.commit()
                    await session.refresh(student_token_usage)
                    response["Success_Log"] += f"StudentTokenUsage committed to DB."
            except Exception as e:
                raise ValueError(f"Invalid student ID for StudentTokenUsage table. Connection denied. (_validate_student() Error: {e})")

        self.student = student
        self.student_name = student.name
        self.student_total_token_usage = student.total_token_usage
        self.student_token_usage = student_token_usage
        response["Success_Log"] += f"Student {student.name} initialized successfully."

        return student, response

    async def _validate_textbook(self, textbook_id: int):
        try:
            response = {"Success_Log": ""}
            async with settings.get_session() as session:
                try:
                    # Get textbook with joined subject and board
                    statement = select(TextBook).where(TextBook.id == textbook_id)
                    result = await session.execute(statement)
                    textbook = result.scalars().first()
                    response["Success_Log"] += f"Textbook {textbook.name} found."
                except Exception as e:
                        raise ValueError(f"Invalid textbook ID for Textbook table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get subject
                    subject_stmt = select(Subject).where(Subject.id == textbook.subject_id)
                    result = await session.execute(subject_stmt)
                    subject = result.scalars().first()
                    self.subject_name = subject.name
                    response["Success_Log"] += f"Subject {subject.name} found."
                except Exception as e:
                    raise ValueError(f"Invalid textbook ID for Subject table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get educational board
                    board_stmt = select(EducationalBoard).where(EducationalBoard.id == textbook.educational_board_id)
                    result = await session.execute(board_stmt)
                    board = result.scalars().first()
                    self.educational_board = board.name
                    response["Success_Log"] += f"Educational board {board.name} found."
                except Exception as e:
                    raise ValueError(f"Invalid textbook ID for EducationalBoard table. Connection denied. (_validate_textbook() Error: {e})")

                try:
                    # Get first standard (many-to-many)
                    std_link_stmt = select(Standard).where(Standard.id == textbook.standard_id)
                    result = await session.execute(std_link_stmt)
                    standards = result.scalars().first()
                    self.standard = standards[0].name if standards else None
                    response["Success_Log"] += f"Standard {self.standard} found."
                except Exception as e:
                    raise ValueError(f"Invalid textbook ID for Standard table. Connection denied. (_validate_textbook() Error: {e})")

            self.textbook = textbook
            self.textbook_code = textbook.code

            return textbook, response

        except Exception as e:
            raise ValueError(f"Invalid textbook ID. Connection denied. (_validate_textbook() Error: {e})")

    async def update_student_token_usage(self, token_count: int):
        self.student_total_token_usage += token_count
        self.student.total_token_usage = self.student_total_token_usage

        self.student_token_usage.token_used += token_count

        async with settings.get_session() as session:
            session.add(self.student)
            session.add(self.student_token_usage)

            await session.commit()

        self.logger.info("[TOKENS] Token usage updated in DB.")

    # RAG Documents
    def add_rag_document(self, document: str):
        if not isinstance(document, str):
            raise ValueError("RAG document must be a string.")
        self.rag_documents.append(document)
        self.logger.info(f"[RAG] Added document: {document[:50]}... (total: {len(self.rag_documents)})")

    def get_rag_documents(self, limit: int = 0) -> List[str]:
        if limit > 0:
            return self.rag_documents[-limit:]
        return self.rag_documents

    # History
    def add_to_history(self, speaker: str, message: str):
        if speaker not in ["user", "assistant"]:
            raise ValueError("Speaker must be 'user' or 'assistant'.")
        super().add_to_history(role=speaker, content=message)

        if len(self.history) > 30:
            self._summarize_history()

    def _summarize_history(self):
        summary_prompt = (
            "Please provide a concise summary of this conversation history. "
            "Focus on the main topics discussed and any important conclusions or decisions made."
        )
        messages = self.get_history()
        summary = llm_client.get_response(
            prompt=summary_prompt,
            context=messages,
            temperature=0.3
        )
        self.history = [{"role": "assistant", "content": f"Summary so far:\n\n'''{summary}'''"}]
        self.logger.info("[HISTORY] Conversation summarized due to excessive length.")

    def clear_conversation_history(self):
        self.history.clear()
        self.logger.info("[HISTORY] Cleared conversation history.")
