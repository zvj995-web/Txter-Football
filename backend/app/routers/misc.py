from fastapi import APIRouter, HTTPException, Query

from app.models.misc import (
    BrainstormOutline, BrainstormOutlineDetail,
    ReferenceArticle, FileItem, SaveRequest, SaveResult,
    ConfigUpdateRequest,
)
from app.services.misc_service import (
    list_brainstorm_outlines, get_brainstorm_outline,
    list_references, list_files, save_file, update_config,
)
from app.services.config_service import load_config

router = APIRouter(tags=["Misc"])


# --- Brainstorm Outlines ---

@router.get("/brainstorm-outlines", response_model=list[BrainstormOutline])
def get_brainstorm_list():
    return list_brainstorm_outlines()


@router.get("/brainstorm-outlines/{filename:path}", response_model=BrainstormOutlineDetail)
def get_brainstorm_detail(filename: str):
    result = get_brainstorm_outline(filename)
    if not result:
        raise HTTPException(404, "Outline not found")
    return result


# --- Reference Articles ---

@router.get("/references", response_model=list[ReferenceArticle])
def get_references(ip: str = Query("")):
    return list_references(ip)


# --- Files ---

@router.get("/files", response_model=list[FileItem])
def get_files(keyword: str = Query("")):
    return list_files(keyword)


# --- Save ---

@router.post("/save", response_model=SaveResult)
async def save_file_endpoint(request: SaveRequest):
    result = await save_file(request)
    if not result.success:
        raise HTTPException(500, result.error)
    return result


# --- Config ---

@router.get("/config")
def get_config():
    return load_config()


@router.post("/config")
def set_config(request: ConfigUpdateRequest):
    try:
        return update_config(request.updates)
    except Exception as e:
        raise HTTPException(500, str(e))
