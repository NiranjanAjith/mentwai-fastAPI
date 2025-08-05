from sqlmodel import SQLModel, Field, select
from typing import Optional
from datetime import date
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession



class Student(SQLModel, table=True):
    __tablename__ = "students_student"

    id: UUID = Field(primary_key=True)
    username: str
    name: str
    admission_number: str
    phone_number: str

    gender: str
    total_token_usage: int
    dob: Optional[date]
    guardian_name: Optional[str]
    guardian_relationship: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]


class StudentTokenUsage(SQLModel, table=True):
    __tablename__ = "students_student_token_usage"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="students_student.id")
    token_used: int = 0
    image_count: int = 0
    date_added: Optional[date] = None



async def ensure_student(session: AsyncSession, student_id: Optional[UUID]) -> UUID:
    if student_id:
        return student_id

    # Lookup anonymous user/student by username/email/etc.
    result = await session.execute(
        select(Student).where(Student.name == "Anonymous")
    )
    student = result.scalar_one_or_none()

    if student:
        return student.id

    # Else create one
    new_student = Student(name="Anonymous")
    session.add(new_student)
    await session.commit()
    await session.refresh(new_student)
    return new_student.id