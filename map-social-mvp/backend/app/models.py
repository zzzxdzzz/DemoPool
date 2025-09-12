from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    hashed_password: str
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    posts: List["Post"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")

class Location(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    kind: str  # restaurant, climbing_gym, ski_resort, city, running_route, hiking_route
    lat: float = Field(index=True)
    lon: float = Field(index=True)
    address: Optional[str] = None
    description: Optional[str] = None
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    posts: List["Post"] = Relationship(back_populates="location")

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: int = Field(foreign_key="location.id", index=True)
    author_id: int = Field(foreign_key="user.id", index=True)
    content: str
    photo_url: Optional[str] = None
    tags: Optional[str] = None  # comma-separated activity tags
    created_at: datetime = Field(default_factory=datetime.utcnow)

    location: "Location" = Relationship(back_populates="posts")
    author: "User" = Relationship(back_populates="posts")
    comments: List["Comment"] = Relationship(back_populates="post")

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    author_id: int = Field(foreign_key="user.id", index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    post: "Post" = Relationship(back_populates="comments")
    author: "User" = Relationship(back_populates="comments")

class SessionEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: int = Field(foreign_key="location.id", index=True)
    host_id: int = Field(foreign_key="user.id", index=True)
    title: str
    activity: str  # running, hiking, bouldering, ski, etc.
    starts_at: datetime
    ends_at: datetime
    max_people: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
