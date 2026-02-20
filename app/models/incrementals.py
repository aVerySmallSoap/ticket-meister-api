import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field


class Incremental(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    stored: int
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        ))
    checked_at: datetime = Field(
        DateTime(timezone=True),
        nullable=False,
    )