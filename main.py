import uuid
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, Query, HTTPException
from sqlmodel import SQLModel, Session, select, create_engine

from app.models.ticket import Ticket, TicketCreate, TicketUpdate

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(ticket: TicketCreate, session: session_dependency):
    ticket.id = uuid.uuid4()
    db_ticket = Ticket.model_validate(ticket)
    session.add(db_ticket)
    session.commit()
    session.refresh(db_ticket)
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
        ticket_id: uuid.UUID,
        session: session_dependency
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    return ticket

@app.delete("/tickets/{ticket_id}")
def delete_ticket(
        ticket_id: uuid.UUID,
        session: session_dependency
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    session.delete(ticket)
    session.commit()
    return {"ok": True}

@app.patch("/tickets/{ticket_id}")
def update_ticket(
        ticket_id: uuid.UUID,
        ticket: TicketUpdate,
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