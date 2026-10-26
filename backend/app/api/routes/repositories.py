"""Repository analysis endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_activity_service,
    get_current_user,
    get_db_client,
    get_github_service,
    get_repository_service,
)
from app.core.security import AuthUser
from app.core.logging import get_logger
from app.core.exceptions import GitHubError
from app.db import repositories as db
from app.schemas.repository import (
    AnalysisDetailResponse,
    AnalysisListResponse,
    AnalysisResponse,
    AnalyzeRequest,
    RecommendationOut,
    RepositorySummary,
)
from app.services.activity_service import ACTIVITY_ANALYSIS, ActivityService
from app.services.repository_service import RepositoryAnalysisService
from app.services.github_service import GitHubService
from app.utils.github_urls import parse_repository_url
from supabase import Client

router = APIRouter(prefix="/repositories", tags=["repositories"])
logger = get_logger(__name__)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    service: RepositoryAnalysisService = Depends(get_repository_service),
    activity_service: ActivityService = Depends(get_activity_service),
) -> AnalysisResponse:
    result = await service.analyze(
        user_id=user.user_id,
        repository_url=request.repository_url,
        issue_count=request.issues,
        top=request.top,
        client=client,
    )
    logger.info("Repository endpoint received analysis result")
    recommendations = [
        RecommendationOut.model_validate(item)
        for item in result["recommendations"]
    ]
    repository = RepositorySummary.model_validate(result["repository"])
    if result.get("id"):
        activity_service.record(
            client,
            user_id=user.user_id,
            activity_type=ACTIVITY_ANALYSIS,
            summary={
                "repository": repository.full_name,
                "recommendations": len(recommendations),
            },
        )
    response = AnalysisResponse(
        id=result.get("id"),
        repository=repository,
        conventions=result["conventions"],
        recommendations=recommendations,
        created_at=result.get("created_at"),
    )
    logger.info("Repository endpoint returning response")
    return response


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
) -> AnalysisListResponse:
    rows = db.list_analyses(client, user.user_id)
    return AnalysisListResponse.model_validate({"analyses": rows})


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: str,
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    github: GitHubService = Depends(get_github_service),
) -> AnalysisDetailResponse:
    row = db.get_analysis(client, user.user_id, analysis_id)
    try:
        metadata = await github.get_repository(parse_repository_url(row["repository_url"]))
    except GitHubError:
        metadata = {
            "owner": row.get("owner"),
            "name": row.get("name"),
            "full_name": f"{row.get('owner')}/{row.get('name')}",
            "description": None,
            "default_branch": "",
            "stargazers_count": 0,
            "language": None,
            "html_url": row.get("repository_url"),
        }
    repository = RepositorySummary.model_validate(metadata)
    return AnalysisDetailResponse(
        id=row.get("id"),
        repository=repository,
        conventions=row.get("conventions") or {},
        recommendations=row.get("recommendations") or [],
        created_at=row.get("created_at"),
        raw=row,
    )
