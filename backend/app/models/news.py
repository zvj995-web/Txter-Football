from pydantic import BaseModel


class NewsSearchRequest(BaseModel):
    keyword: str = ""


class NewsResult(BaseModel):
    text: str
