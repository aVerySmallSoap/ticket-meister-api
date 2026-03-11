import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

class TokenBase(SQLModel):
    id: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        )
    )

class RefreshToken(TokenBase, table=True):
    __tablename__ = 'refresh_tokens'

    id: uuid.UUID = Field(primary_key=True)
    token_hash: str
    user_id: str = Field(foreign_key='users.id')
    expires_at: datetime
    revoked: bool = Field(default=False)
    revoked_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        )
    )

# Pydantic Models

#TODO: If you can, bind this to refresh tokens and remove the ACCESS_TOKEN_EXPIRE_MINUTES on .env
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None