from uuid import UUID
from sqlmodel import SQLModel, Field

class PersonnelBase(SQLModel):
    name: str | None = Field()

class Personnel(PersonnelBase, table=True):
    id: UUID = Field(index=True, primary_key=True)

class PersonnelUpdate(PersonnelBase):
    name: str