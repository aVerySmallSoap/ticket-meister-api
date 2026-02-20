# mock data
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine, select

from app.models.ticket import Ticket

mock_ticket = {
    "id": "1f32333c-6b15-4902-80ad-273e7b299cf7",
    "name": "Test Ticket",
    "email": "test@ticket.net",
    "office": "ticket-meister",
    "request_type": 0,
    "details": "This is a test ticket.",
    "date": "2024-06-01T12:00:00Z",
    "priority": 0,
    "personnel": None
}

#Database setup
sqlite_test_db_file = "test_database.db"
sqlite_url = f"sqlite:///{sqlite_test_db_file}"

connection_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connection_args)
def get_session():
    with Session(engine) as session:
        yield session

session_dependency = Annotated[Session, Depends(get_session)]

# ticket creation tests
def on_create(client, session: session_dependency):
    # We assume that the request body is valid and that the endpoint will return a 201 status code if the ticket is created successfully.
    # We also check if the ticket is actually created in the database by querying for it using its ID.
    response = client.post("/tickets", json=mock_ticket)
    data = response.json()
    assert response.status_code == 201
    ticket_to_validate = session.exec(select(Ticket).where(Ticket.id == data["id"])).first()
    assert ticket_to_validate is not None
    cleanup(client, ticket_to_validate.id)

def create_en_masse(client, session: session_dependency):
    # We create multiple tickets and check if they are all created successfully and that they all exist in the database.

    # fail this test if any of the ticket creations fail.
    created_ticket_ids = []
    for i in range(5):
        response = client.post("/tickets", json=mock_ticket)
        data = response.json()
        assert response.status_code == 201
        created_ticket_ids.append(data["id"])

    for ticket_id in created_ticket_ids:
        ticket_to_validate = session.exec(select(Ticket).where(Ticket.id == ticket_id)).first()
        assert ticket_to_validate is not None
        cleanup(client, ticket_to_validate.id)

def cleanup(client, ticket_id):
    client.delete(f"/tickets/{ticket_id}")