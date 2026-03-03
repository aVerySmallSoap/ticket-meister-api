# This file contains all request types
from uuid import UUID

from pydantic import BaseModel


class PersonnelList(BaseModel):
    ids: list[UUID]