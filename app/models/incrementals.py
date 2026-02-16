import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field


class Incremental(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    stored: int
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default_factory= lambda: datetime.now(ZoneInfo("Asia/Manila")),
        ))
    checked_at: datetime = Field(
        DateTime(timezone=True),
        nullable=False,
        default_factory= lambda: datetime.now(ZoneInfo("Asia/Manila")),
    )