"""Screenshot triage endpoint (multipart upload)."""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.ai.provider import ImageInput
from app.api.deps import (
    get_activity_service,
    get_current_user,
    get_db_client,
    get_settings,
    get_triage_service,
)
from app.core.config import Settings
from app.core.security import AuthUser
from app.schemas.triage import TriageResponse
from app.services.activity_service import ACTIVITY_TRIAGE, ActivityService
from app.services.triage_service import TriageService, clean_note
from app.utils.images import validate_image
from supabase import Client

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("", response_model=TriageResponse)
async def triage_screenshot(
    repository_url: str = Form(...),
    image: UploadFile = File(...),
    note: str | None = Form(default=None),
    user: AuthUser = Depends(get_current_user),
    client: Client = Depends(get_db_client),
    settings: Settings = Depends(get_settings),
    service: TriageService = Depends(get_triage_service),
    activity_service: ActivityService = Depends(get_activity_service),
) -> TriageResponse:
    data = await image.read()
    mime = validate_image(data, max_bytes=settings.max_upload_bytes)
    screenshot = ImageInput(mime_type=mime, data=data)

    result = await service.triage(
        user_id=user.user_id,
        repository_url=repository_url,
        image=screenshot,
        note=clean_note(note),
        client=client,
    )
    activity_service.record(
        client,
        user_id=user.user_id,
        activity_type=ACTIVITY_TRIAGE,
        summary={
            "repository": result["repository"]["full_name"],
            "errors": len(result["analysis"].visible_errors),
        },
    )
    return TriageResponse.model_validate(result)
