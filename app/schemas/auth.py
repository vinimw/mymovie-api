from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    message: str = "Login successful."


class MeResponse(BaseModel):
    email: str
