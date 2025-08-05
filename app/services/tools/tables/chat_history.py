from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field

from app.services.tools.tables.base_table import BaseModel



class ChatSession(BaseModel, table=True):
    __tablename__ = "student_chat_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="students_student.id", index=True)
    textbook_id: UUID = Field(foreign_key="academics_textbooks.id", index=True)

    title: Optional[str] = Field(default=None, max_length=255)
    history: Optional[str] = Field(default="", description="Short preview of the conversation")
    file_path: str = Field(max_length=500)


    def __str__(self):
        return f"{self.id})"

