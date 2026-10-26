"""User profile schemas."""

from __future__ import annotations

from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: str
    email: str | None
    display_name: str
