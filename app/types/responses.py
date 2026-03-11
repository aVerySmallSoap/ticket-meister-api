from http import HTTPStatus
from http.client import HTTPException

from pydantic import BaseModel


class Response:
    _message: str
    _code: HTTPStatus
    _status: str

    def message(self, message: str):
        self._message = message
        return self

    def code(self, code: HTTPStatus):
        self._code = code
        return self

    def status(self, status: str):
        self._status = status
        return self

    def json(self) -> dict:
        return {"message": self._message, "code": self._code, "status": self._status}

    def appended(self, **kwargs) -> dict:
        """Returns a response with custom appended data"""
        return {"message": self._message, "code": self._code, "status": self._status, **kwargs}

    def throw(self):
        raise HTTPException()

class ResponseModel(BaseModel):
    message: str
    code: HTTPStatus
    status: str