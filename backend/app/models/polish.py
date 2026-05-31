from pydantic import BaseModel


class AudioPolishRequest(BaseModel):
    text: str
    iterate: bool = False
    previousResult: str | None = None
    instruction: str | None = None


class AudioPolishResult(BaseModel):
    polished: str
