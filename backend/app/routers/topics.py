from fastapi import APIRouter, HTTPException

from app.models.topics import (
    TopicLibraryOut, TopicOut,
    DimensionAddRequest, TopicGenerateRequest, TopicAppendRequest,
    TopicRefineRequest,
)
from app.services.topic_service import (
    list_all_libraries, get_library, get_random_topic,
    add_dimension, generate_candidates, append_topic, refine_topic,
)

router = APIRouter(tags=["Topics"])


@router.get("/topics", response_model=list[TopicLibraryOut])
def all_topic_libraries():
    return list_all_libraries()


@router.get("/topics/{skill_id}", response_model=TopicLibraryOut)
def get_topic_library(skill_id: str):
    lib = get_library(skill_id)
    if not lib:
        raise HTTPException(404, "Topic library not found")
    return lib


@router.get("/topics/{skill_id}/random", response_model=TopicOut)
def random_topic(skill_id: str):
    topic = get_random_topic(skill_id)
    if not topic:
        raise HTTPException(404, "No topics available for this skill")
    return topic


@router.post("/topics/{skill_id}/dimension", response_model=TopicLibraryOut)
def add_dimension_endpoint(skill_id: str, request: DimensionAddRequest):
    try:
        return add_dimension(skill_id, request.dimensionName, request.description)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/topics/{skill_id}/generate", response_model=list[TopicOut])
async def generate_candidates_endpoint(skill_id: str, request: TopicGenerateRequest):
    try:
        return await generate_candidates(
            skill_id=skill_id,
            dimension=request.dimension,
            news_material=request.newsMaterial,
            brainstorm=request.brainstorm,
            count=request.count,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/topics/{skill_id}/append", response_model=TopicLibraryOut)
def append_topic_endpoint(skill_id: str, request: TopicAppendRequest):
    try:
        request.skillId = skill_id
        return append_topic(request)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/topics/{skill_id}/refine", response_model=TopicOut)
async def refine_topic_endpoint(skill_id: str, request: TopicRefineRequest):
    request.skillId = skill_id
    try:
        return await refine_topic(request)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
