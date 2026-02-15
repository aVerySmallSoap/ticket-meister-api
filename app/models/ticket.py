from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

from app.types import RequestType, Priorities


class TicketBase(SQLModel):
    name: str
    email: str = Field(index=True)
    office: str
    request_type: RequestType
    details: str | None = Field(default=None)

class Ticket(TicketBase, table=True):
    date: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        )
    )
    id: UUID = Field(index=True, primary_key=True)
    priority: Priorities = Field(default=Priorities.NONE)
    personnel: str | None = Field(default=None)

class PersonnelUpdate(TicketBase):
    priority: Priorities
    personnel: str | None