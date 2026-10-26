"""Authenticated user endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db_client
from app.core.security import AuthUser
from app.db import repositories as db
from app.schemas.user import UserResponse
from supabase import Client

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_me(
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
) -> UserResponse:
    profile = db.get_user_profile(client, user.user_id)
    display_name = (profile or {}).get("display_name") or user.display_name()
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=display_name,
    )
