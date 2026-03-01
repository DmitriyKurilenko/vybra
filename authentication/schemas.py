"""
Authentication schemas for Django Ninja API
"""
from ninja import Schema
from typing import Optional


class RegisterSchema(Schema):
    email: str
    password: str
    username: Optional[str] = None


class LoginSchema(Schema):
    email: str
    password: str


class TokenSchema(Schema):
    success: bool = True
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class UserSchema(Schema):
    id: int
    email: str
    username: str


class RefreshTokenSchema(Schema):
    refresh_token: Optional[str] = None


class AuthMessageSchema(Schema):
    success: bool
    message: str
