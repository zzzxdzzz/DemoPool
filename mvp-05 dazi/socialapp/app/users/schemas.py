from pydantic import BaseModel

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    bio: str | None = None

    class Config:
        from_attributes = True
