"""Dashboard endpoint: aggregate counts and recent activity."""

from fastapi import APIRouter, Depends

from app.api.deps import get_activity_service, get_current_user, get_db_client
from app.core.security import AuthUser
from app.schemas.dashboard import DashboardResponse
from app.services.activity_service import ActivityService
from supabase import Client

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def read_dashboard(
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    activity_service: ActivityService = Depends(get_activity_service),
) -> DashboardResponse:
    data = activity_service.dashboard(client, user_id=user.user_id)
    return DashboardResponse.model_validate(data)
