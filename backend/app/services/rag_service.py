import json
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from google import genai

from app.core.config import settings
from app.models.rag import (
    RagChunk, RagQueryRequest, RagQueryResponse, PipelineInfo,
    RagAggregateRequest, RagAggregateResponse, AggregatedReport,
)

_chroma_client: ClientAPI | None = None
_gemini_client: Any = None
_team_map: dict | None = None

PIPELINES = [
    PipelineInfo(key="whoscored", label="📊 whoscored", description="WhoScored 赛前技战术报告"),
    PipelineInfo(key="api-football", label="📋 api-football", description="API-Football 联赛数据"),
    PipelineInfo(key="odds", label="💰 odds", description="赔率走势分析"),
    PipelineInfo(key="understat-pre", label="📐 understat-pre", description="xG 预期数据（赛前）"),
    PipelineInfo(key="understat-post", label="📐 understat-post", description="xG 实际数据（赛后）"),
    PipelineInfo(key="fotmob", label="📱 fotmob", description="FotMob 实时数据"),
    PipelineInfo(key="polymarket", label="🗳️ polymarket", description="Polymarket 预测市场"),
    PipelineInfo(key="inoreader", label="📰 inoreader", description="Inoreader RSS 新闻"),
    PipelineInfo(key="djyy", label="📡 djyy", description="djyy 联赛数据"),
    PipelineInfo(key="grok-news", label="🤖 grok-news", description="Grok 新闻分析"),
    PipelineInfo(key="grok-footballworld", label="🌍 grok-footballworld", description="Grok 足球世界"),
]

PIPELINE_LABELS = {p.key: p.label for p in PIPELINES}


def _get_chroma():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
    return _chroma_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _load_team_map() -> dict:
    global _team_map
    if _team_map is None:
        with open(settings.team_map_path, "r", encoding="utf-8") as f:
            _team_map = json.load(f)
    return _team_map


def _resolve_team(team_name: str) -> str:
    """Resolve a team name to a normalized form for matching against ChromaDB metadata."""
    if not team_name:
        return ""
    name = team_name.strip().lower()
    team_map = _load_team_map()
    teams = team_map.get("teams", {})

    # Check if the name is an English key
    if name in teams:
        return name

    # Check aliases
    for key, info in teams.items():
        for alias in info.get("aliases", []):
            if alias == name:
                return key

    # Check if it's a Chinese name
    for key, info in teams.items():
        if info.get("cn", "").lower() == name:
            return key
        for alias in info.get("cn_aliases", []):
            if alias.lower() == name:
                return key

    # Fallback: return as-is
    return name


def _team_matches(metadata: dict, home_team: str, away_team: str | None) -> bool:
    """Check if a chunk's metadata matches the given teams."""
    meta_home = (metadata.get("home_team") or "").lower()
    meta_away = (metadata.get("away_team") or "").lower()
    text = meta_home + meta_away

    if home_team.lower() in text:
        if away_team:
            return away_team.lower() in text
        return True
    return False


def query_rag(request: RagQueryRequest) -> RagQueryResponse:
    if not settings.gemini_api_key:
        return RagQueryResponse(chunks=[], totalFound=0)

    chroma = _get_chroma()
    gemini_cli = _get_gemini()

    try:
        coll = chroma.get_collection(settings.chroma_collection)
    except Exception:
        return RagQueryResponse(chunks=[], totalFound=0)

    # Keyword mode: free-text search, no team filtering
    use_keyword = bool(request.keyword.strip())
    home = _resolve_team(request.homeTeam) if request.homeTeam else ""
    away = _resolve_team(request.awayTeam) if request.awayTeam else None

    if use_keyword:
        query_text = request.keyword
    else:
        query_parts = [f"Match: {request.homeTeam}"]
        if request.awayTeam:
            query_parts.append(f"vs {request.awayTeam}")
        if request.matchDate:
            query_parts.append(f"Date: {request.matchDate}")
        query_text = " ".join(query_parts)

    # Get embedding
    emb_result = gemini_cli.models.embed_content(
        model="gemini-embedding-2",
        contents=query_text,
    )
    query_embedding = list(emb_result.embeddings[0].values)

    # Build metadata filter (pipeline only)
    where = None
    if request.pipelines:
        where = {"pipeline": {"$in": request.pipelines}}

    search_n = max(request.topK * 3, 30)
    results = coll.query(
        query_embeddings=[query_embedding],
        n_results=search_n,
        where=where,
        include=["metadatas", "documents", "distances"],
    )

    chunks = []
    seen_ids = set()
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Team filter only in non-keyword mode
        if not use_keyword and not _team_matches(meta, home, away):
            continue

        chunk_id = f"{meta.get('pipeline','')}-{meta.get('filename','')}-{meta.get('chunk_index','')}"
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)

        pipeline = meta.get("pipeline", "")
        relevance = max(0, min(100, round((1 - dist) * 100)))

        full_text = doc or ""
        snippet = full_text[:200] + ("..." if len(full_text) > 200 else "")

        chunks.append(RagChunk(
            id=chunk_id,
            pipeline=pipeline,
            pipelineLabel=PIPELINE_LABELS.get(pipeline, pipeline),
            title=meta.get("section", "") or meta.get("filename", "") or "Untitled",
            snippet=snippet,
            relevance=relevance,
            fullText=full_text,
        ))

        if len(chunks) >= request.topK:
            break

    chunks.sort(key=lambda c: c.relevance, reverse=True)

    return RagQueryResponse(chunks=chunks, totalFound=len(chunks))


def get_pipelines() -> list[PipelineInfo]:
    return PIPELINES


def aggregate_rag(request: RagAggregateRequest) -> RagAggregateResponse:
    chroma = _get_chroma()
    home = _resolve_team(request.homeTeam)
    away = _resolve_team(request.awayTeam) if request.awayTeam else None

    try:
        coll = chroma.get_collection(settings.chroma_collection)
    except Exception:
        return RagAggregateResponse(reports=[], totalFound=0)

    # Only use pipeline + match_date in ChromaDB where (exact match)
    # Team filtering is done client-side because ChromaDB stores teams with prefixes like 【API】Arsenal
    where = None
    if request.matchDate:
        where = {"match_date": request.matchDate}

    pipeline_filter = None
    if request.pipelines:
        pipeline_filter = {"pipeline": {"$in": request.pipelines}}
        where = {"$and": [where, pipeline_filter]} if where else pipeline_filter

    try:
        results = coll.get(
            where=where,
            include=["metadatas", "documents"],
            limit=500,
        )
    except Exception:
        return RagAggregateResponse(reports=[], totalFound=0)

    # Client-side team + pipeline filtering
    reports_by_key: dict[str, AggregatedReport] = {}
    for doc, meta in zip(results["documents"] or [], results["metadatas"] or []):
        if not _team_matches(meta, home, away):
            continue

        pipeline = meta.get("pipeline", "")
        filename = meta.get("filename", "")
        key = f"{pipeline}|{filename}"

        if key in reports_by_key:
            reports_by_key[key].fullText += "\n\n" + (doc or "")
        else:
            reports_by_key[key] = AggregatedReport(
                pipeline=pipeline,
                pipelineLabel=PIPELINE_LABELS.get(pipeline, pipeline),
                filename=filename,
                fullText=doc or "",
                metadata={k: v for k, v in meta.items() if k not in ("pipeline", "filename")},
            )

    reports = sorted(reports_by_key.values(), key=lambda r: (r.pipeline, r.filename))
    return RagAggregateResponse(reports=reports, totalFound=len(reports))
