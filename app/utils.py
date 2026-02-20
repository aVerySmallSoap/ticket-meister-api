import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine
from sqlmodel import Session, select

from app.models.incrementals import Incremental

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