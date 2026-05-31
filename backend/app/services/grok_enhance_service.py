import httpx

from app.core.config import settings

API_URL = "https://api.x.ai/v1/responses"

ENHANCE_SYSTEM_PROMPT = """你是足球内容研究员。请为以下选题寻找支撑论据。

规则：
1. 必须调用 web_search + x_search 获取最新信息。
2. 搜索关键词基于选题标题和逻辑，寻找相关的最新数据、统计、案例、行业分析。
3. 返回纯文本，包含具体的数字、来源、事件名称。不要泛泛而谈。
4. 如果找不到相关信息，返回空，不要编造。
5. 最多 2000 字，精炼有效信息。"""


async def enhance_news_context(topic_title: str, topic_logic: str, news_material: str) -> str:
    """Use Grok with web_search to find supplementary evidence for a news-driven topic."""
    grok_key = settings.grok_api_key
    if not grok_key:
        return ""

    user_msg = f"""选题标题：{topic_title}
选题逻辑：{topic_logic}

原始新闻素材：
{news_material[:2000]}

请搜索与上述选题角度相关的最新数据、统计、案例分析，补充到素材中。"""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {grok_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.grok_model,
                    "input": [
                        {"role": "system", "content": ENHANCE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "tools": [{"type": "web_search"}, {"type": "x_search"}],
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                },
            )

        if resp.status_code != 200:
            return ""

        data = resp.json()
        if data.get("error"):
            return ""

        text = ""
        for item in reversed(data.get("output", [])):
            if item.get("type") == "message" and item.get("role") == "assistant":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        text = c.get("text", "")
                        break

        return text.strip() if text else ""

    except Exception:
        return ""
