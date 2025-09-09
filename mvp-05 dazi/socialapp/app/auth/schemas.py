from pydantic import BaseModel, Field, EmailStr

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
