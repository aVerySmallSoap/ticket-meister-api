from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

from app.types.app_types import RequestType, Status, Priorities


class TicketBase(SQLModel):
    name: str
    email: str = Field(index=True)
    office: str
    request_type: RequestType
    details: str | None = Field(default=None)

class Ticket(TicketBase, table=True):
    __tablename__ = 'tickets'

    date: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        ),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    id: str = Field(index=True, primary_key=True)
    priority: Priorities = Field(default=Priorities.NONE)
    # personnel: List[str] | None = Field(default=None, sa_column=Column(ARRAY(String))) # Use a list if possible in MariaDB
    personnel: str = Field(default='None')
    status: Status = Field(default=Status.PENDING)

class PersonnelUpdate(TicketBase):
    priority: Priorities
    # personnel: List[str] | None =Field(sa_column=Column(ARRAY(String))) # Use a list if possible in MariaDB
    personnel: str | None
    status: Status