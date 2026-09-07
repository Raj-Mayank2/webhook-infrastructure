from pydantic import BaseModel, HttpUrl

class WebhookCreate(BaseModel):
    url:HttpUrl


class WebhookResponse(BaseModel):
    id:int
    url:str
    secret:str

    class Config:
        from_attributes=True