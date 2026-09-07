from typing import Any

from pydantic import BaseModel


class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]


class EventResponse(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]

    class Config:
        from_attributes = True