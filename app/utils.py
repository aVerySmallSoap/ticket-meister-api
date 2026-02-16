from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select, create_engine

from models.incrementals import Incremental
from models.ticket import Ticket

sqlite_test_db_file = "test_database.db"
sqlite_url = f"sqlite:///../{sqlite_test_db_file}"

connection_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connection_args)

# Fetch how many row we have in the database based on the current month.
def fetch_all_tickets(session: Session) -> int:
    try:
        rows = session.exec(select(Ticket)).all()
        if rows is None:
            return 0
        return len(rows)
    except Exception as e:
        print("Something went wrong")
        print(e)
    return 0

def check_and_store_increment(id_tracker: int, session: Session):
    """Checks if the database is currently up-to-date with the in memory incremental counter. This update will always push to the database."""
    try:
        updated_timestamp = datetime.now(ZoneInfo("Asia/Manila"))
        row = session.exec(select(Incremental)).first() # There will always be a singular entry
        if row is None:
            # Create and store the current value of the tracker
            row = Incremental.model_construct(stored=0)
            session.add(row)
            session.commit()
            session.refresh(row)
            return 0
        row.stored = id_tracker
        row.checked_at = updated_timestamp
        row.updated_at = updated_timestamp
        session.add(row)
        session.commit()
        session.refresh(row)
        return id_tracker
    except Exception as e:
        print(e)

def create_unique_id(id_tracker: int)-> str:
    """Creates a unique id set for a ticket. The format is YEAR-MONTH-INCREMENT"""
    timestamp = datetime.now(ZoneInfo("Asia/Manila"))
    month, year = timestamp.month, timestamp.year
    return str(year) + str(month) + str(id_tracker)

print(fetch_all_tickets())