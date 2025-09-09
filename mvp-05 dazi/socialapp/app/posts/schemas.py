from pydantic import BaseModel
from datetime import datetime

class PostIn(BaseModel):
    content: str

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str
    media_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class CommentIn(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
