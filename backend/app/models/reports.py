from pydantic import BaseModel


class ReportOut(BaseModel):
    path: str
    sourceKey: str
    sourceLabel: str
    filename: str
    mtime: float
    snippet: str = ""
