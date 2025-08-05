import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Boolean, DateTime, Integer, select, func

from app.core.config import settings



class BaseModel(SQLModel):
    __abstract__ = True

    auto_id: int = Field(
        sa_column=Column("auto_id", nullable=False, unique=True, index=True)
    )
    creator_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    updater_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    date_added: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=False),
    )
    date_updated: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True),
    )
    is_deleted: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, default=False),
    )



async def populate_base_fields(obj, user_id):
    now = datetime.now().date()
    model_class = obj.__class__
    async with settings.get_session() as session:
        result = await session.execute(select(func.max(model_class.auto_id)))
        max_auto_id = result.scalar()

    obj.auto_id = (max_auto_id or 0) + 1
    obj.date_added = now
    obj.date_updated = now
    obj.is_deleted = False

    return obj
