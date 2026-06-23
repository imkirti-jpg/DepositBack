from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class AsyncJobResponse(BaseModel):
    id: str
    status: str      
    poll_url: str    