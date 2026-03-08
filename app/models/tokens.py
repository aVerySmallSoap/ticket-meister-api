from datetime import datetime

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

class RefreshToken(TokenBase, table=True, tablename='refresh_tokens'):
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