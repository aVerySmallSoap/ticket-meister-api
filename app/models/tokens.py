import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

class TokenBase(SQLModel):
    id: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        ),
        default_factory=lambda: datetime.now(timezone.utc),
    )

class RefreshToken(TokenBase, table=True):
    __tablename__ = 'refresh_tokens'

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    token_hash: str
    user_id: str = Field(foreign_key='users.id')
    expires_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False
        )
    )
    revoked: bool = Field(default=False)
    revoked_at: datetime | None = Field(
        sa_column=Column(
            DateTime(timezone=True),
        )
    )

# Pydantic Models

#TODO: If you can, bind this to refresh tokens and remove the ACCESS_TOKEN_EXPIRE_MINUTES on .env
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None