from pydantic import BaseModel, Field


class BasicUser(BaseModel):
    email: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    display_name: str
    other_users: list[BasicUser] = []


class MeResponse(BaseModel):
    email: str
    display_name: str
    other_users: list[BasicUser] = []
