from pydantic import BaseModel


class CopywritingGenerationRequest(BaseModel):
    skillId: str
    topic: dict | None = None
    targetLength: int = 800
    constraint: str = "strict"
    brainstormOutline: str | None = None
    references: list[str] = []


class CopywritingGenerationResult(BaseModel):
    content: str
    skillId: str


class WechatGenerationRequest(BaseModel):
    skillId: str
    reports: list[dict] = []
    thesis: str = ""
    references: list[dict] = []
    selectedChunks: list[dict] = []


class NodeResults(BaseModel):
    node1: str = ""
    node2: str = ""
    node3: str = ""
    node4: str = ""


class WechatGenerationResult(BaseModel):
    nodeResults: NodeResults
    finalArticle: str


class ShortVideoConvertRequest(BaseModel):
    text: str


class ShortVideoConvertResult(BaseModel):
    variants: list[dict]  # [{type: "version_a", hook: "...", body: "...", cta: "..."}, ...]
