from fastapi import APIRouter

from app.models.rag import (
    RagQueryRequest, RagQueryResponse, PipelineInfo,
    RagAggregateRequest, RagAggregateResponse,
)
from app.services.rag_service import query_rag, get_pipelines, aggregate_rag

router = APIRouter(tags=["RAG"])


@router.post("/rag/query", response_model=RagQueryResponse)
async def rag_query(request: RagQueryRequest):
    return query_rag(request)


@router.post("/rag/aggregate", response_model=RagAggregateResponse)
async def rag_aggregate(request: RagAggregateRequest):
    return aggregate_rag(request)


@router.get("/pipelines", response_model=list[PipelineInfo])
def pipelines():
    return get_pipelines()
