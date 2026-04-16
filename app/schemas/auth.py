from pydantic import BaseModel, EmailStr, Field


class UserRegistration(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class InviteDelegateRequest(BaseModel):
    full_name: str
    email: EmailStr


class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str = Field(..., min_length=8, max_length=128)
