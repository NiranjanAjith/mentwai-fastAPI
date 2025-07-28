from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID
from typing import List


class TextBookStandardLink(SQLModel, table=True):
    __tablename__ = "academics_textbooks_standard"
    
    textbook_id: UUID = Field(foreign_key="academics_textbooks.id", primary_key=True)
    standard_id: UUID = Field(foreign_key="academics_standard.id", primary_key=True)


class Standard(SQLModel, table=True):
    __tablename__ = "academics_standard"

    id: UUID = Field(default=None, primary_key=True)
    name: str

    text_books: List["TextBook"] = Relationship(
        back_populates="standards",
        link_model=TextBookStandardLink
    )



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
    
    standards: List["Standard"] = Relationship(
        back_populates="text_books",
        link_model=TextBookStandardLink
    )
