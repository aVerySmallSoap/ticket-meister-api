import uuid

from sqlmodel import SQLModel


class Notification(SQLModel, table=True):
    id: str | uuid.UUID
