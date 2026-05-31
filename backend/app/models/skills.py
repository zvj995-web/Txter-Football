from typing import Any
from pydantic import BaseModel


class SkillOut(BaseModel):
    rawId: str
    name: str
    description: str
    tags: list[str]
    content: str
    path: str
    manifest: dict[str, Any] | None = None
