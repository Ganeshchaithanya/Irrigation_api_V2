"""
Pydantic Schemas — Auth
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any


class RegisterRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str
    confirm_password: str
    preferred_lang: Optional[str] = "en"

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Allow digits, plus, hyphens, spaces, and parentheses
        clean_v = v.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        if clean_v and not clean_v.isdigit():
            raise ValueError("Invalid phone number format. Use digits and common separators.")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class LoginRequest(BaseModel):
    identifier: str   # email or phone
    password: str

class GoogleLoginRequest(BaseModel):
    email: str
    name: str
    google_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: Any  # UUID
    preferred_lang: str


class UserResponse(BaseModel):
    id: Any  # UUID
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    preferred_lang: str
    avatar_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
