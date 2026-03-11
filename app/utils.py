import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import bcrypt
import jwt
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.models.incrementals import Incremental
from app.models.user import User

# Auth related functions

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

def verify_password(password: str, password_hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hashed.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), os.getenv("ALGORITHM"))
    return encoded_jwt

# Database related utils

#!IMPORTANT! This function also returns none if a basic validation fails
#TODO: Create another function that returns an exception on validation fail.
#TODO: Check for SQL INJECTION or XSS attempts
def authenticate_user(username: str, password: str, session: Session):
    """Checks if the user exists on the database."""
    if len(username.strip()) == 0 or len(password) == 0 or username.strip() == "":
        return None

    #Check if email exists
    user_db = session.exec(
        select(User).where(User.email == username)
    ).one_or_none()
    if not user_db:
        return None

    user = User.model_validate(user_db)
    if not verify_password(password, user.password):
        return None
    return user

def check_and_store_increment(id_tracker: int, engine: Engine):
    """Checks if the database is currently up-to-date with the in memory incremental counter. This update will always push to the database."""
    with Session(engine) as session:
        try:
            updated_timestamp = datetime.now(ZoneInfo("Asia/Manila"))
            row = session.exec(statement=select(Incremental)).first() # There will always be a singular entry
            if row is None:
                # Create and store the current value of the tracker
                row = Incremental(id=uuid.uuid4() ,stored=0, updated_at=updated_timestamp, checked_at=updated_timestamp)
                session.add(row)
                session.commit()
                session.refresh(row)
                return
            row.stored = id_tracker
            row.checked_at = updated_timestamp
            row.updated_at = updated_timestamp
            session.add(row)
            session.commit()
            session.refresh(row)
        except Exception as e:
            print(e)

def check_and_retrieve_increment(engine: Engine) -> int:
    with Session(engine) as session:
        try:
            row = session.exec(statement=select(Incremental)).first() # There will always be a singular entry
            if row is None:
                return 0
            return row.stored
        except Exception as e:
            print(e)
        return 0

def create_unique_id(id_tracker: int)-> str:
    """Creates a unique id set for a ticket. The format is YEAR-MONTH-INCREMENT"""
    timestamp = datetime.now(ZoneInfo("Asia/Manila"))
    month, year = timestamp.month, timestamp.year
    return f"{str(year)}-{str(month)}-{str(id_tracker)}"