from fastapi import APIRouter, HTTPException

from app.models.news import NewsSearchRequest, NewsResult
from app.services.news_service import fetch_trending_news, search_news

router = APIRouter(tags=["News"])


@router.post("/news/trending", response_model=NewsResult)
async def trending_endpoint():
    try:
        return await fetch_trending_news()
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/news/search", response_model=NewsResult)
async def search_endpoint(request: NewsSearchRequest):
    try:
        return await search_news(request.keyword)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
