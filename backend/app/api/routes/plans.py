"""Contribution plan endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_activity_service,
    get_current_user,
    get_db_client,
    get_plan_service,
)
from app.core.security import AuthUser
from app.db import repositories as db
from app.schemas.plan import (
    PlanCreateRequest,
    PlanListResponse,
    PlanResponse,
)
from app.schemas.dashboard import ActivityItem
from app.services.activity_service import ACTIVITY_PLAN, ActivityService
from app.services.plan_service import PlanService
from supabase import Client

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanResponse)
async def create_plan(
    request: PlanCreateRequest,
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    service: PlanService = Depends(get_plan_service),
    activity_service: ActivityService = Depends(get_activity_service),
) -> PlanResponse:
    result = await service.generate_plan(
        user_id=user.user_id,
        repository_url=request.repository_url,
        issue_number=request.issue_number,
        client=client,
    )
    activity_service.record(
        client,
        user_id=user.user_id,
        activity_type=ACTIVITY_PLAN,
        summary={
            "repository": result["repository"]["full_name"],
            "issue_number": result["issue"]["number"],
        },
    )
    return PlanResponse.model_validate(result, from_attributes=False)


@router.get("", response_model=PlanListResponse)
async def list_plans(
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
) -> PlanListResponse:
    rows = db.list_plans(client, user.user_id)
    return PlanListResponse.model_validate({"plans": rows})


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
) -> PlanResponse:
    row = db.get_plan(client, user.user_id, plan_id)
    return PlanResponse(
        id=row.get("id"),
        repository={
            "owner": row.get("repository_url", "").rstrip("/").split("/")[-2:][0],
            "name": row.get("repository_url", "").rstrip("/").split("/")[-1],
            "html_url": row.get("repository_url"),
        },
        issue={
            "number": row.get("issue_number"),
            "title": row.get("issue_title"),
        },
        plan=row.get("plan") or {},
        created_at=row.get("created_at"),
    )
