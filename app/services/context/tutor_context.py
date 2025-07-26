from datetime import timezone, datetime
from typing import Dict, List

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tools.tables.student import Student, StudentTokenUsage
from app.services.tools.tables.textbook import (
    TextBook,
    Subject,
    EducationalBoard,
    Standard,
    Medium,
    textbook_standard_link,
    textbook_medium_link
)
from app.services.tools.llm import llm_client
from app.framework.context import BaseContext



class TutorContext(BaseContext):
    def __init__(self, project_name: str = "tutor"):
        super().__init__(project_name=project_name)

        # RAG documents
        self.rag_documents: List[str] = []

    async def initialize(self, student_id: int, textbook_id: int):
        self.student_id = student_id
        self.student = await self._validate_student(student_id)
        self.textbook = await self._validate_textbook(textbook_id)

    async def _validate_student(self, user_id: int, session: AsyncSession):
        stmt = select(Student).where(Student.id == user_id)
        result = await session.exec(stmt)
        student = result.first()

        if not student:
            raise ValueError("Invalid student ID. Connection denied.")

        self.student = student
        self.student_name = student.name
        self.student_total_token_usage = student.total_token_usage

        today = datetime.now(timezone.utc).date()

        stmt_usage = select(StudentTokenUsage).where(
            StudentTokenUsage.date_added == today,
            StudentTokenUsage.student_id == student.id
        )
        result_usage = await session.exec(stmt_usage)
        student_token_usage = result_usage.first()

        if not student_token_usage:
            student_token_usage = StudentTokenUsage(
                student_id=student.id,
                date_added=today
            )
            session.add(student_token_usage)
            await session.commit()
            await session.refresh(student_token_usage)

        self.student_token_usage = student_token_usage
        return student

    async def _validate_textbook(self, textbook_id: int):
        try:
            # Get textbook with joined subject and board
            statement = select(TextBook).where(TextBook.id == textbook_id)
            textbook = (await self.session.exec(statement)).first()
            if not textbook:
                raise ValueError("Invalid textbook ID. Connection denied.")

            self.textbook = textbook
            self.textbook_code = textbook.code

            # Get subject
            subject_stmt = select(Subject).where(Subject.id == textbook.subject_id)
            subject = (await self.session.exec(subject_stmt)).first()
            self.subject_name = subject.name

            # Get educational board
            board_stmt = select(EducationalBoard).where(EducationalBoard.id == textbook.educational_board_id)
            board = (await self.session.exec(board_stmt)).first()
            self.educational_board = board.name

            # Get first standard (many-to-many)
            std_link_stmt = select(Standard).join(textbook_standard_link).where(
                textbook_standard_link.c.textbook_id == textbook.id
            )
            standards = (await self.session.exec(std_link_stmt)).all()
            self.standard = standards[0].name if standards else None

            return textbook

        except Exception as e:
            raise ValueError("Invalid textbook ID. Connection denied.") from e

    async def update_student_token_usage(self, token_count: int, session: AsyncSession):
        self.student_total_token_usage += token_count
        self.student.total_token_usage = self.student_total_token_usage

        self.student_token_usage.token_used += token_count

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
