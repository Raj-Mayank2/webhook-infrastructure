from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    event_type: str


class SubscriptionResponse(BaseModel):
    id: int
    event_type: str

    class Config:
        from_attributes = True