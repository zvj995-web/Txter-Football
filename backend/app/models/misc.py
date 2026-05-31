from pydantic import BaseModel


class BrainstormOutline(BaseModel):
    filename: str
    title: str = ""
    coreLogic: str = ""
    compliance: str = ""


class BrainstormOutlineDetail(BaseModel):
    filename: str
    content: str


class ReferenceArticle(BaseModel):
    path: str
    filename: str


class FileItem(BaseModel):
    path: str
    filename: str
    sourceKey: str
    sourceLabel: str


class SaveRequest(BaseModel):
    content: str
    filename: str
    folder: str = ""           # "copywriting" | "polish" | "wechat"
    ip: str = ""               # "persona" | "yssq"
    skillId: str = ""


class SaveResult(BaseModel):
    success: bool
    savedPath: str = ""
    error: str = ""


class ConfigUpdateRequest(BaseModel):
    updates: dict
