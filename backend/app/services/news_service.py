import json
import httpx

from app.core.config import settings
from app.models.news import NewsResult

API_URL = "https://api.x.ai/v1/responses"

SYSTEM_PROMPT = """你现在是足球热点新闻采集专家，严格进入【Zero Hallucination Mode】。

铁律：
1. 强制工具优先：必须先调用 web_search + x_search 获取真实信息，禁止使用任何历史内置知识。
2. 时间锚点验证：每条新闻必须明确写出信息的时间窗口。优先输出最近 12 小时内的新闻，超过 24 小时的直接跳过，除非该事件在 24 小时内有重大新进展。
3. 时效性优先：如果有更新的信息覆盖了旧闻（如比赛已结束，赛前名单就没价值了），必须输出最新状态而非旧状态。
4. 绝对禁止：把已经离任的教练/球员仍当成现任，使用旧转会传闻当新消息。
5. 原文素材保留：从搜索到的原文中提取关键段落、直接引语、具体数据，完整保留在输出中。这是后续 AI 选题生成的核心素材，信息量越大越好。

输出格式：
每条新闻用 <news> ... </news> 包裹，包含四个板块：
**事件详情**
**原文摘录**（从源文章中提取的关键段落、直接引语、数据细节，尽量详实，不少于 200 字）
**X 舆论反应**
**业内人士态度**

最多 10 条，高质量优先，不够就少输出。"""


async def _call_grok(user_message: str, max_tokens: int = 8192) -> str:
    body = {
        "model": settings.grok_model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "tools": [{"type": "web_search"}, {"type": "x_search"}],
        "temperature": 0.95,
        "max_output_tokens": max_tokens,
        "top_p": 0.95,
        "reasoning_effort": "high",
    }

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {settings.grok_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Grok API error: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Grok API error: {data['error']}")

    text = ""
    for item in reversed(data.get("output", [])):
        if item.get("type") == "message" and item.get("role") == "assistant":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text = c.get("text", "")
                    break

    if not text:
        raise RuntimeError("Grok returned no output text")

    return text


async def fetch_trending_news() -> NewsResult:
    text = await _call_grok(
        "请搜索过去 12 小时内全球足球最新热点新闻，按指定格式输出（最多 10 条，按时间倒序）。如果某事件已有更新进展（如比赛已结束），只输出最新状态。",
        max_tokens=4096,
    )
    return NewsResult(text=text)


async def search_news(keyword: str) -> NewsResult:
    text = await _call_grok(
        f"请搜索以下足球新闻的详细信息，按指定格式输出。请务必找到真实来源：\n\n{keyword}",
        max_tokens=4096,
    )
    return NewsResult(text=text)
