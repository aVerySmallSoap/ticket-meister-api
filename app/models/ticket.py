from datetime import datetime
from typing import List

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field, ARRAY, String

from app.app_types import RequestType, Priorities


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
    id: str = Field(index=True, primary_key=True)
    priority: Priorities = Field(default=Priorities.NONE)
    # personnel: List[str] | None = Field(default=None, sa_column=Column(ARRAY(String))) # Use a list if possible in MariaDB
    personnel: str | None

class PersonnelUpdate(TicketBase):
    priority: Priorities
    # personnel: List[str] | None =Field(sa_column=Column(ARRAY(String))) # Use a list if possible in MariaDB
    personnel: str | None