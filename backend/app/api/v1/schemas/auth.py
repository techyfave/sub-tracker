from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "ada@example.com",
                    "password": "ExamplePass123!",
                }
            ]
        }
    )

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "ada@example.com",
                    "password": "ExamplePass123!",
                }
            ]
        }
    )

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "refresh_token": "your-refresh-token-here",
                }
            ]
        }
    )

    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "ada@example.com",
                    "created_at": "2026-10-14T10:30:00Z",
                }
            ]
        }
    )

    id: UUID
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "your-access-token-here",
                    "refresh_token": "your-refresh-token-here",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "ada@example.com",
                        "created_at": "2026-10-14T10:30:00Z",
                    },
                    "tokens": {
                        "access_token": "your-access-token-here",
                        "refresh_token": "your-refresh-token-here",
                        "token_type": "bearer",
                    },
                }
            ]
        }
    )

    user: UserResponse
    tokens: TokenResponse
