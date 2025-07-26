from sqlalchemy import Table, Column, ForeignKey
from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as SAUUID  # For PostgreSQL UUID support


class TextBook(SQLModel, table=True):
    __tablename__ = "academics_textbook"
    id: UUID = Field(default=None, primary_key=True)
    code: str
    retrieve_prompt: Optional[str] = None
    subject_id: UUID = Field(foreign_key="academics_subject.id")
    educational_board_id: UUID = Field(foreign_key="academics_educationalboard.id")


class Standard(SQLModel, table=True):
    __tablename__ = "academics_standard"
    id: UUID = Field(default=None, primary_key=True)
    name: str


class Medium(SQLModel, table=True):
    __tablename__ = "academics_medium"
    id: UUID = Field(default=None, primary_key=True)
    name: str


class Subject(SQLModel, table=True):
    __tablename__ = "academics_subjects"

    id: UUID = Field(primary_key=True)
    name: str
    retrieve_prompt: Optional[str] = None


class EducationalBoard(SQLModel, table=True):
    __tablename__ = "academics_educational_board"

    id: UUID = Field(primary_key=True)
    name: str




# Link table for textbook <-> standard (many-to-many)
textbook_standard_link = Table(
    "academics_textbook_standard",  # Use actual table name from your DB
    SQLModel.metadata,
    Column("textbook_id", SAUUID(as_uuid=True), ForeignKey("academics_textbook.id"), primary_key=True),
    Column("standard_id", SAUUID(as_uuid=True), ForeignKey("academics_standard.id"), primary_key=True),
)

# Link table for textbook <-> medium (many-to-many)
textbook_medium_link = Table(
    "academics_textbook_medium",
    SQLModel.metadata,
    Column("textbook_id", SAUUID(as_uuid=True), ForeignKey("academics_textbook.id"), primary_key=True),
    Column("medium_id", SAUUID(as_uuid=True), ForeignKey("academics_medium.id"), primary_key=True),
)
