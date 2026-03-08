import uuid
from sqlmodel import SQLModel, Field

from app.types.app_types import Roles

class UserBase(SQLModel):
    email: str
    full_name: str


class User(UserBase, table=True, tablename='users'):
    id: uuid.UUID = Field(primary_key=True)
    password: str
    role: Roles = Field(default=Roles.Technician)