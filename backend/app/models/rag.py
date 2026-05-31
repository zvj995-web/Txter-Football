from pydantic import BaseModel


class RagQueryRequest(BaseModel):
    homeTeam: str = ""
    awayTeam: str | None = None
    matchDate: str | None = None
    pipelines: list[str] = []
    topK: int = 10
    keyword: str = ""  # free-text keyword search, bypasses team filtering


class RagChunk(BaseModel):
    id: str
    pipeline: str
    pipelineLabel: str
    title: str
    snippet: str
    relevance: int
    fullText: str


class RagQueryResponse(BaseModel):
    chunks: list[RagChunk]
    totalFound: int


class PipelineInfo(BaseModel):
    key: str
    label: str
    description: str


class RagAggregateRequest(BaseModel):
    homeTeam: str
    awayTeam: str | None = None
    matchDate: str | None = None
    pipelines: list[str] = []
    mode: str = "full"  # "full" or "summary"


class AggregatedReport(BaseModel):
    pipeline: str
    pipelineLabel: str
    filename: str
    fullText: str
    metadata: dict = {}


class RagAggregateResponse(BaseModel):
    reports: list[AggregatedReport]
    totalFound: int
