import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import bcrypt
import jwt
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.models.incrementals import Incremental
from app.models.user import User
from app.types.app_types import RequestType


# Auth related functions

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

def verify_password(password: str, password_hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hashed.encode('utf-8'))

def create_access_token(user: User) -> str:
    # We can use a User object here since we already verify it through authenticate_user()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))).timestamp()), # Might bite perf later
    }
    encoded_jwt = jwt.encode(payload, os.getenv("SECRET_KEY"), os.getenv("ALGORITHM"))
    return encoded_jwt

def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# Database related utils

#!IMPORTANT! This function also returns none if a basic validation fails
#TODO: Create another function that returns an exception on validation fail.
#TODO: Check for SQL INJECTION or XSS attempts
def authenticate_user(username: str, password: str, session: Session) -> Optional[User]:
    """Checks if the user exists on the database."""
    if len(username.strip()) == 0 or len(password) == 0 or username.strip() == "":
        return None

    #Check if email exists
    user = session.exec(
        select(User).where(User.email == username)
    ).one_or_none()
    if not user:
        return None
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

# PDF related functions

def map_ticket_to_pdf(ticket):
    req = ticket.request_type

    return {
        "SRFNO": ticket.id,
        "FULLNAME": ticket.name,
        "CONTACTNO": "",
        "DATE": ticket.date.strftime("%Y-%m-%d"),
        "EMAIL": ticket.email,

        "HARDWARE": "Yes" if req == RequestType.hardware_repairs_and_configuration else "Off",

        "NETWORK": "Yes" if req == RequestType.network_or_internet_services else "Off",

        "DATA": "Yes" if req == RequestType.data_services else "Off",

        "SYSTEM": "Yes" if req == RequestType.system_services else "Off",

        "DEVELOPMENT": "Yes" if req == RequestType.request_for_system_development else "Off",

        "OTHERS": "Yes" if req == RequestType.others else "Off",

        "OTHERS_DETAILS": ticket.details if req == RequestType.others else "",

        "DETAILS": ticket.details,

        "PERSONNEL": str(ticket.personnel),

        "C_DATE": ticket.date.strftime("%Y-%m-%d"),

        "ACTIONTAKEN": "",

        "PERSONNELSIG": "",

        "DEPARTMENT": ticket.office,

        "REQUESTOR": ticket.name,
    }