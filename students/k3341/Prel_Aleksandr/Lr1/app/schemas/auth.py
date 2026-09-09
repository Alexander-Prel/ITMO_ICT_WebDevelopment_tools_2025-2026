from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.users import UserRead


class RegisterRequest(BaseModel):
    name: str = Field(description="Имя пользователя")
    last_name: Optional[str] = Field(default=None, max_length=100, description="Фамилия, необязательное поле")
    email: str
    password: str
    city: Optional[str] = None
    contact_info: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    user: UserRead


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
