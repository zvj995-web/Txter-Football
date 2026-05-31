from fastapi import APIRouter, Query

from app.models.skills import SkillOut
from app.services.skill_service import load_all_skills, filter_by_type

router = APIRouter(tags=["Skills"])


@router.get("/skills", response_model=list[SkillOut])
def get_skills(type: str | None = Query(None)):
    skills = load_all_skills()
    if type:
        skills = filter_by_type(skills, type)
    return skills
