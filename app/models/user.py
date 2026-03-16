import uuid

from pydantic import BaseModel
from sqlmodel import SQLModel, Field

from app.types.app_types import Roles

class UserBase(SQLModel):
    email: str
    full_name: str

class User(UserBase, table=True):
    __tablename__ = 'users'

    id: uuid.UUID = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    password: str
    role: Roles = Field(default=Roles.Technician)

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: uuid.UUID
    role: Roles

# Request Types

class UserList(BaseModel):
    ids: list[uuid.UUID]

class LoginRequest(BaseModel):
    email: str
    password: str