import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.generation import (
    CopywritingGenerationRequest,
    CopywritingGenerationResult,
    WechatGenerationRequest,
    WechatGenerationResult,
    NodeResults,
    ShortVideoConvertRequest,
    ShortVideoConvertResult,
)
from app.services.skill_service import load_all_skills
from app.services.generation_service import run_copywriting, run_wechat_pipeline, run_wechat_pipeline_stream, convert_to_short_video
from app.services.grok_enhance_service import enhance_news_context

router = APIRouter(tags=["Generation"])


def _resolve_constraint(manifest: dict | None, constraint_key: str) -> str:
    """Resolve a constraint key (e.g. 'strict') to the prompt text from manifest."""
    if not manifest:
        return ""
    constraints = manifest.get("constraints", [])
    for c in constraints:
        if c.get("key") == constraint_key:
            return c.get("prompt", "")
    return ""


@router.post("/generate/copywriting", response_model=CopywritingGenerationResult)
async def generate_copywriting(request: CopywritingGenerationRequest):
    skills = load_all_skills()
    skill = next((s for s in skills if s.rawId == request.skillId), None)
    if not skill:
        raise HTTPException(404, "Skill not found")

    topic = request.topic or {}
    constraint_prompt = _resolve_constraint(skill.manifest, request.constraint)

    # Creative mode + news material → Grok enhances context with real-time web search
    news_material = topic.get("news_material", "")
    if request.constraint == "creative" and news_material:
        enhanced = await enhance_news_context(
            topic_title=topic.get("title", ""),
            topic_logic=topic.get("logic", ""),
            news_material=news_material,
        )
        if enhanced:
            news_material = f"{news_material}\n\n---\n【Grok 实时搜索补充素材】\n{enhanced}"

    content = await run_copywriting(
        skill_content=skill.content,
        topic_title=topic.get("title", ""),
        topic_logic=topic.get("logic", ""),
        topic_core_thesis=topic.get("core_thesis", ""),
        topic_common_belief=topic.get("common_belief", ""),
        topic_data_required=topic.get("data_required", ""),
        topic_reader_hook=topic.get("reader_hook", ""),
        topic_news_hook=topic.get("news_hook", ""),
        topic_news_material=news_material,
        target_length=request.targetLength,
        constraint=constraint_prompt,
        brainstorm_outline=request.brainstormOutline or "",
        context_files=request.references if request.references else None,
    )
    return CopywritingGenerationResult(content=content, skillId=request.skillId)


@router.post("/generate/wechat", response_model=WechatGenerationResult)
async def generate_wechat(request: WechatGenerationRequest):
    skills = load_all_skills()
    skill = next((s for s in skills if s.rawId == request.skillId), None)
    if not skill:
        raise HTTPException(404, "Skill not found")

    result = await run_wechat_pipeline(
        skill_content=skill.content,
        raw_id=request.skillId,
        reports=request.reports,
        thesis=request.thesis,
        references=request.references,
        selected_chunks=request.selectedChunks,
    )

    if "error" in result:
        raise HTTPException(500, result["error"])

    return WechatGenerationResult(
        nodeResults=NodeResults(
            node1=result["nodeResults"]["node1"],
            node2=result["nodeResults"]["node2"],
            node3=result["nodeResults"]["node3"],
            node4=result["nodeResults"]["node4"],
        ),
        finalArticle=result["finalArticle"],
    )


@router.post("/generate/wechat/stream")
async def generate_wechat_stream(request: WechatGenerationRequest):
    skills = load_all_skills()
    skill = next((s for s in skills if s.rawId == request.skillId), None)
    if not skill:
        raise HTTPException(404, "Skill not found")

    async def event_stream():
        async for event in run_wechat_pipeline_stream(
            skill_content=skill.content,
            raw_id=request.skillId,
            reports=request.reports,
            thesis=request.thesis,
            references=request.references,
            selected_chunks=request.selectedChunks,
        ):
            yield {"data": event}

    return EventSourceResponse(event_stream())


@router.post("/convert/short-video", response_model=ShortVideoConvertResult)
async def convert_short_video(request: ShortVideoConvertRequest):
    try:
        variants = await convert_to_short_video(request.text)
        return ShortVideoConvertResult(variants=variants)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
