from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import Column, text, DateTime
from sqlmodel import SQLModel, Field

from app.types.request_type import RequestType
from app.types.priorities import Priorities


class TicketBase(SQLModel):
    date: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    name: str
    email: str = Field(index=True)
    office: str
    request_type: RequestType
    details: str | None = Field(default=None)

class Ticket(TicketBase, table=True):
    id: UUID = Field(index=True, primary_key=True)
    priority: Priorities = Field(default=Priorities.NONE)
    personnel: str | None = Field(default=None)

class TicketCreate(TicketBase):
    id: UUID

class TicketUpdate(TicketBase):
    priority: Priorities
    personnel: str | None