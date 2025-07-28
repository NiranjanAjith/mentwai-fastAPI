from sqlmodel import SQLModel, Field
from uuid import UUID


class Standard(SQLModel, table=True):
    __tablename__ = "academics_standard"
    id: UUID = Field(default=None, primary_key=True)
    name: str


class Subject(SQLModel, table=True):
    __tablename__ = "academics_subjects"

    id: UUID = Field(primary_key=True)
    name: str


class EducationalBoard(SQLModel, table=True):
    __tablename__ = "academics_educational_board"

    id: UUID = Field(primary_key=True)
    name: str


class TextBook(SQLModel, table=True):
    __tablename__ = "academics_textbooks"
    id: UUID = Field(default=None, primary_key=True)
    code: str
    name: str
    subject_id: UUID = Field(foreign_key="academics_subjects.id")
    educational_board_id: UUID = Field(foreign_key="academics_educational_board.id")
    standard_id: UUID = Field(foreign_key="academics_standard.id")