from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    password: str

class UserPublic(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Location
class LocationCreate(BaseModel):
    title: str
    kind: str
    lat: float
    lon: float
    address: Optional[str] = None
    description: Optional[str] = None

class LocationPublic(BaseModel):
    id: int
    title: str
    kind: str
    lat: float
    lon: float
    address: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

# Post
class PostCreate(BaseModel):
    location_id: int
    content: str
    photo_url: Optional[str] = None
    tags: Optional[str] = None

class PostPublic(BaseModel):
    id: int
    location_id: int
    author_id: int
    content: str
    photo_url: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Comment
class CommentCreate(BaseModel):
    post_id: int
    content: str

class CommentPublic(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

# Session
class SessionCreate(BaseModel):
    location_id: int
    title: str
    activity: str
    starts_at: datetime
    ends_at: datetime
    max_people: Optional[int] = None
    notes: Optional[str] = None

class SessionPublic(BaseModel):
    id: int
    location_id: int
    host_id: int
    title: str
    activity: str
    starts_at: datetime
    ends_at: datetime
    max_people: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
