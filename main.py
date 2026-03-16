import os
import shutil
import time
import uuid
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Optional

import jwt
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends, Query, HTTPException, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response
from fastapi_cloud_cli.commands.login import TokenResponse
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject
from sqlalchemy import String
from sqlmodel import SQLModel, Session, select, create_engine, cast
from starlette.responses import FileResponse

from app.models.ticket import Ticket, PersonnelUpdate
from app.models.user import User, UserCreate, UserPublic, UserList
from app.models.tokens import Token, RefreshToken
from app.utils import check_and_retrieve_increment, create_unique_id, check_and_store_increment, hash_password, \
    authenticate_user, create_access_token, create_refresh_token, hash_refresh_token, map_ticket_to_pdf
from app.types.app_types import Roles

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

oauth_scheme = OAuth2PasswordBearer(tokenUrl="auth")

async def get_current_user(
        token: Annotated[str, Depends(oauth_scheme)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    #JWT implementation
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except Exception: # Too general of a catch
        raise credentials_exception

    user_id = uuid.UUID(sub)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User does not exist!"
        )
    return user

# Authentication endpoints
@app.post("/auth")
def authenticate(
        response: Response,
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
    access_token = create_access_token(user)
    raw_refresh_token = create_refresh_token()
    refresh_token_db = RefreshToken(
        user_id=str(user.id), #BIND TO UUID later
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    )
    session.add(refresh_token_db)
    session.commit()

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=False, #prod should be True
        samesite="lax",
        max_age=(int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) * 60),
        path="/auth"
    )

    return Token(access_token=access_token, token_type="bearer")

@app.post("/auth/refresh")
def refresh_access_token(
        response: Response,
        session: session_dependency,
    refresh_token: Optional[str] = Cookie(default=None)
):
    if not refresh_token:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="missing refresh token"
        )

    token_hash = hash_refresh_token(refresh_token)

    db_token = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="invalid refresh token"
        )
    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="refresh token expired"
        )

    user = session.get(User, uuid.UUID(db_token.user_id))
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="user not found"
        )
    db_token.revoked = True
    new_raw_refresh_token = create_refresh_token()
    new_db_token = RefreshToken(
        user_id=str(user.id),
        token_hash=hash_refresh_token(new_raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    )
    session.add(new_db_token)
    session.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh_token,
        httponly=True,
        secure=False,  # prod should be True
        samesite="lax",
        max_age=(int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) * 60),
        path="/auth"
    )

    return TokenResponse(access_token=create_access_token(user))

@app.post("/auth/logout")
def logout(
        response: Response,
        session: session_dependency,
        refresh_token: Optional[str] = Cookie(default=None),
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        db_token = session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).one_or_none()
        if db_token:
            db_token.revoked = True
            session.add(db_token)
            session.commit()

    response.delete_cookie(key="refresh_token", path="/auth")
    return {"status": "ok"}

@app.get("/auth/me", response_model=UserPublic)
def get_logged_user(current_user: Annotated[User, Depends(get_current_user)]):
    return UserPublic(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )

# Ticket endpoints

@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(ticket: Ticket, session: session_dependency):
    # TICKETS ARE NOT PROTECTED BY OAUTH NOR JWT, IT IS A PUBLIC FACING ENDPOINT
    # EXTRA SECURITY CHECKS ARE NEED FOR SQLINJECTION, XSS ATTACKS, MALFORMED INPUT, ETC.
    # STRICT COOKIES SHOULD BE ADHERED SUCH AS ACCESS-CONTROL-ALLOW-ORIGIN to DNSC.EDU.PH/*

    # Year - Month - Increment
    global id_lock, id_tracker
    while id_lock:
        # Do not use the id tracker until the lock is released. This is to prevent race conditions.
        time.sleep(5)
    id_lock = True
    gen_id = create_unique_id(id_tracker)
    id_tracker += 1

    # Create and store ticket into database
    # TODO: Might need checks for FK's on Users
    ticket.id = gen_id
    db_ticket = Ticket.model_validate(ticket)
    session.add(db_ticket)
    session.commit()
    session.refresh(db_ticket)

    id_lock = False
    check_and_store_increment(id_tracker, engine) # This will be heavy on I/O usage, need better code for this check
    return db_ticket # Should not return this, it might contain info about the DB. Return a generic OK response

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

@app.post("/user")
def create_user(user: UserCreate, session: session_dependency):
    try:
        #TODO: Check if email is valid.

        # check if email already exists
        existing = session.exec(select(User).where(User.email == user.email)).first()

        if existing:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="user already exists"
            )
        hashed_password = hash_password(user.password)

        model_dump = user.model_dump()
        model_dump["password"] = hashed_password

        user = User.model_construct(**model_dump)
        db_user = User.model_validate(user)

        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return {"status": "ok"}
    except Exception as error:
        # log error
        print(error)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )

@app.get("/users", response_model=list[UserPublic])
def read_personnel(
        token: Annotated[str, Depends(get_current_user)],
        session: session_dependency,
        offset:int = 0,
        limit: Annotated[int, Query(le=100)] = 100
):
    personnel = session.exec(select(User).where(User.role != Roles.Admin).offset(offset).limit(limit)).all()
    return personnel

@app.get("/user/{user_id}")
def get_personnel(
        user_id: uuid.UUID,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.get(User, user_id)
    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Personnel Not Found"
        )
    return ticket

@app.post("/user/list")
def get_user_list(
        user_list: UserList,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    # SQLite stores UUIDs as string so we need to cast it all to string
    ids_as_str = [str(u) for u in user_list.ids]
    stmt = select(User).where(cast(User.id, String).in_(ids_as_str)).where(User.role != Roles.Admin)
    rows = session.exec(stmt).all()
    if not rows:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="personnel not found"
        )
    return rows

@app.delete("/user/{user_id}")
def delete_user(
        user_id: uuid.UUID,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.get(User, user_id)
    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Personnel Not Found"
        )
    session.delete(ticket)
    session.commit()

@app.patch("/user/{user_id}")
def update_user(
        user_id: uuid.UUID,
        personnel: PersonnelUpdate,
        session: session_dependency,
        token: Annotated[str, Depends(get_current_user)]
):
    user_db = session.get(User, user_id)
    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Ticket Not Found"
        )
    user_data = personnel.model_dump(exclude_unset=True)
    user_db.sqlmodel_update(user_data)
    session.add(user_db)
    session.commit()
    session.refresh(user_db)
    return user_db

@app.post("/export/pdf")
def export_pdf(
    ticket_id: str,
    session: session_dependency,
    token: Annotated[str, Depends(get_current_user)]
):
    ticket = session.exec(
        select(Ticket).where(Ticket.id == ticket_id)
    ).one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Ticket Not Found"
        )

    name = f"{uuid.uuid4()}.pdf"
    output_path = os.path.join("jonk", name)

    reader = PdfReader("FORM.pdf")
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    writer._root_object[NameObject("/AcroForm")].update({
        NameObject("/NeedAppearances"): BooleanObject(True)
    })

    fields = map_ticket_to_pdf(ticket)

    writer.update_page_form_field_values(
        writer.pages[0],
        fields,
        auto_regenerate=True
    )

    # force checkbox appearance state
    for page in writer.pages:
        annots = page.get("/Annots", [])
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if annot.get("/Subtype") == "/Widget" and annot.get("/FT") == "/Btn":
                field_name = annot.get("/T")
                if not field_name:
                    continue

                value = fields.get(field_name)
                if value == "Yes":
                    annot.update({
                        NameObject("/V"): NameObject("/Yes"),
                        NameObject("/AS"): NameObject("/Yes"),
                    })
                else:
                    annot.update({
                        NameObject("/V"): NameObject("/Off"),
                        NameObject("/AS"): NameObject("/Off"),
                    })

    with open(output_path, "wb") as f:
        writer.write(f)

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=f"{ticket.id}.pdf"
    )