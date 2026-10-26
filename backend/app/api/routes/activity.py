"""Activity history endpoint."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_activity_service, get_current_user, get_db_client
from app.core.security import AuthUser
from app.schemas.dashboard import ActivityListResponse
from app.services.activity_service import ActivityService
from supabase import Client

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=ActivityListResponse)
async def read_activity(
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    activity_service: ActivityService = Depends(get_activity_service),
    limit: int = Query(default=30, ge=1, le=100),
) -> ActivityListResponse:
    items = activity_service.list(client, user_id=user.user_id, limit=limit)
    return ActivityListResponse.model_validate({"activity": items})
