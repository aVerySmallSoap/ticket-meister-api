import datetime
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy import String
from sqlmodel import SQLModel, Session, select, create_engine, cast

from app.models.personnel import Personnel
from app.models.ticket import Ticket, PersonnelUpdate
from app.utils import check_and_retrieve_increment, create_unique_id, check_and_store_increment
from app.types.request_types import PersonnelList

#Database setup
sqlite_test_db_file = "test_database.db"
sqlite_url = f"sqlite:///{sqlite_test_db_file}"

connection_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connection_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

session_dependency = Annotated[Session, Depends(get_session)]

# Setup incremental id tracker
id_tracker: int
id_lock: bool = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global id_tracker
    create_db_and_tables()
    id_tracker = check_and_retrieve_increment(engine)
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"]
)

# Ticket endpoints

@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(ticket: Ticket, session: session_dependency):
    # Year - Month - Increment
    global id_lock, id_tracker
    while id_lock:
        # Do not use the id tracker until the lock is released. This is to prevent race conditions.
        time.sleep(5)
    id_lock = True
    gen_id = create_unique_id(id_tracker)
    id_tracker += 1

    # Create and store ticket into database
    ticket.id = gen_id
    ticket.date = datetime.datetime.now(ZoneInfo("Asia/Manila"))
    db_ticket = Ticket.model_validate(ticket)
    session.add(db_ticket)
    session.commit()
    session.refresh(db_ticket)

    id_lock = False
    check_and_store_increment(id_tracker, engine) # This will be heavy on I/O usage, need better code for this check
    return db_ticket

@app.get("/tickets/", response_model=list[Ticket])
def read_tickets(
        session: session_dependency,
        offset:int = 0,
        limit: Annotated[int, Query(le=100)] = 100
):
    tickets = session.exec(select(Ticket).offset(offset).limit(limit)).all()
    return tickets

@app.get("/tickets/{ticket_id}")
def get_ticket(
        ticket_id: str,
        session: session_dependency
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    return ticket

@app.delete("/tickets/{ticket_id}")
def delete_ticket(
        ticket_id: str,
        session: session_dependency
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    session.delete(ticket)
    session.commit()
    return {"ok": True}

@app.put("/tickets/{ticket_id}")
def update_ticket(
        ticket_id: str,
        ticket: PersonnelUpdate,
        session: session_dependency
):
    ticket_db = session.get(Ticket, ticket_id)
    if not ticket_db:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    ticket_data = ticket.model_dump(exclude_unset=True)

    ticket_db.sqlmodel_update(ticket_data)
    session.add(ticket_db)
    session.commit()
    session.refresh(ticket_db)
    return ticket_db

# Personnel endpoints

@app.post("/personnel", response_model=Personnel)
def create_personnel(personnel: Personnel, session: session_dependency):
    personnel.id = uuid.uuid4()
    db_personnel = Personnel.model_validate(personnel)
    session.add(db_personnel)
    session.commit()
    session.refresh(db_personnel)
    return db_personnel

@app.get("/personnel", response_model=list[Personnel])
def read_personnel(
        session: session_dependency,
        offset:int = 0,
        limit: Annotated[int, Query(le=100)] = 100
):
    personnel = session.exec(select(Personnel).offset(offset).limit(limit)).all()
    return personnel

@app.get("/personnel/{personnel_id}")
def get_personnel(
        personnel_id: uuid.UUID,
        session: session_dependency
):
    ticket = session.get(Personnel, personnel_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    return ticket

@app.post("/personnel/list")
def get_personnel_list(
        personnel: PersonnelList,
        session: session_dependency
):
    # SQLite stores UUIDs as string so we need to cast it all to string
    ids_as_str = [str(u) for u in personnel.ids]
    stmt = select(Personnel).where(cast(Personnel.id, String).in_(ids_as_str))
    rows = session.exec(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    return rows

@app.delete("/personnel/{personnel_id}")
def delete_personnel(
        personnel_id: uuid.UUID,
        session: session_dependency
):
    ticket = session.get(Personnel, personnel_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    session.delete(ticket)
    session.commit()
    return {"ok": True}

@app.patch("/personnel/{personnel_id}")
def update_personnel(
        personnel_id: uuid.UUID,
        personnel: PersonnelUpdate,
        session: session_dependency
):
    personnel_db = session.get(Personnel, personnel_id)
    if not personnel_db:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    personel_data = personnel.model_dump(exclude_unset=True)
    personnel_db.sqlmodel_update(personel_data)
    session.add(personnel_db)
    session.commit()
    session.refresh(personnel_db)
    return personnel_db