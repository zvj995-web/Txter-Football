from fastapi import APIRouter

from app.models.polish import AudioPolishRequest, AudioPolishResult
from app.services.polish_service import polish_text, polish_iterate as do_polish_iterate

router = APIRouter(tags=["Polish"])


@router.post("/polish", response_model=AudioPolishResult)
async def polish(request: AudioPolishRequest):
    result = await polish_text(request.text, request.instruction or "")
    return AudioPolishResult(polished=result)


@router.post("/polish/iterate", response_model=AudioPolishResult)
async def polish_iterate_route(request: AudioPolishRequest):
    result = await do_polish_iterate(
        text=request.text,
        instruction=request.instruction or "",
        previous_result=request.previousResult or "",
    )
    return AudioPolishResult(polished=result)
