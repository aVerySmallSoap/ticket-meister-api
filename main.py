import datetime
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from http import HTTPStatus
from typing import Annotated
from zoneinfo import ZoneInfo

import dotenv
import jwt
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.exc import InvalidTokenError
from sqlalchemy import String
from sqlmodel import SQLModel, Session, select, create_engine, cast

from app.models.ticket import Ticket, PersonnelUpdate
from app.models.user import User, UserCreate, UserPublic, UserList
from app.models.tokens import TokenData, Token
from app.types.responses import Response, ResponseModel
from app.utils import check_and_retrieve_increment, create_unique_id, check_and_store_increment, hash_password, \
    authenticate_user, create_access_token

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
    load_dotenv()
    id_tracker = check_and_retrieve_increment(engine)
    yield

app = FastAPI(lifespan=lifespan)

# Change later if domain is available
# Each request should have CORS-same-site-origin set to strict
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

# Security stuff

oauth_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
        token: Annotated[str, Depends(oauth_scheme)],
        session: Annotated[Session, Depends(get_session)]
):
    #JWT implementation
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        username = payload.get("sub")
        if username is None:
            raise InvalidTokenError
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    user = session.exec(select(User).where(User.email == token_data.username)).one_or_none()
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User does not exist!"
        )
    return user

# Authentication endpoints
@app.post("/token")
def authenticate(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: session_dependency
) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

# Ticket endpoints

@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(ticket: Ticket, session: session_dependency, token: Annotated[str, Depends(get_current_user)]):
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
        token: Annotated[str, Depends(get_current_user)],
        session: session_dependency,
        offset:int = 0,
        limit: Annotated[int, Query(le=100)] = 100,
):
    tickets = session.exec(select(Ticket).offset(offset).limit(limit)).all()
    return tickets

@app.get("/tickets/{ticket_id}")
def get_ticket(
        ticket_id: str,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    return ticket

@app.delete("/tickets/{ticket_id}")
def delete_ticket(
        ticket_id: str,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
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
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
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

# User endpoints

@app.post("/user", response_model=ResponseModel)
def create_user(user: UserCreate, session: session_dependency):
    try:
        #TODO: Check if email is valid.

        # check if email already exists
        existing = session.exec(select(User).where(User.email == user.email)).first()

        if existing:
            return Response().code(HTTPStatus.CONFLICT).status("error").message("User already exists!").json()
        hashed_password = hash_password(user.password)

        model_dump = user.model_dump()
        model_dump["id"] = uuid.uuid4()
        model_dump["password"] = hashed_password

        user = User.model_construct(**model_dump)
        db_user = User.model_validate(user)

        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return Response().code(HTTPStatus.OK).status("ok").message("test").json()
    except Exception as error:
        # log error
        print(error)
        raise HTTPException(status_code=500)

@app.get("/users", response_model=list[UserPublic])
def read_personnel(
        token: Annotated[str, Depends(get_current_user)],
        session: session_dependency,
        offset:int = 0,
        limit: Annotated[int, Query(le=100)] = 100
):
    personnel = session.exec(select(User).offset(offset).limit(limit)).all()
    return personnel

@app.get("/user/{user_id}")
def get_personnel(
        user_id: uuid.UUID,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.get(User, user_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    return ticket

@app.post("/user/list")
def get_user_list(
        user_list: UserList,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    # SQLite stores UUIDs as string so we need to cast it all to string
    ids_as_str = [str(u) for u in user_list.ids]
    stmt = select(User).where(cast(User.id, String).in_(ids_as_str))
    rows = session.exec(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    return rows

@app.delete("/user/{user_id}")
def delete_user(
        user_id: uuid.UUID,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.get(User, user_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Personnel Not Found")
    session.delete(ticket)
    session.commit()
    return {"ok": True}

@app.patch("/user/{user_id}")
def update_user(
        user_id: uuid.UUID,
        personnel: PersonnelUpdate,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    user_db = session.get(User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="Ticket Not Found")
    user_data = personnel.model_dump(exclude_unset=True)
    user_db.sqlmodel_update(user_data)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)
    return user_db