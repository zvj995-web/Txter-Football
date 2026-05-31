import os
import re
import json
from typing import AsyncGenerator

from app.core.dependencies import get_ds_client
from app.services.sensitive_word_service import load_sensitive_word_map, apply_replacements
from app.services.skill_service import load_all_skills

WECHAT_PERSONA_DEFAULTS = {
    "txter-persona-": "你是转体世界波（Turning World Class）的微信公众号主编。",
    "txter-football-yssq-": "你是弈神说球（YS Soccer）的微信公众号主编。",
}


def _extract_wechat_persona(skill_content: str, raw_id: str) -> str:
    for line in (skill_content or "").split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            return f"你是{line[2:].strip()}的微信公众号主编。"
    for prefix, persona in WECHAT_PERSONA_DEFAULTS.items():
        if (raw_id or "").startswith(prefix):
            return persona
    return "你是一名专业的体育类微信公众号主编。"


def _strip_markdown(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_persona_skill(raw_id: str) -> bool:
    return (raw_id or "").startswith("txter-persona-")


async def run_copywriting(
    skill_content: str,
    topic_title: str = "",
    topic_logic: str = "",
    topic_core_thesis: str = "",
    topic_common_belief: str = "",
    topic_data_required: str = "",
    topic_reader_hook: str = "",
    topic_news_hook: str = "",
    topic_news_material: str = "",
    target_length: int = 800,
    constraint: str = "",
    brainstorm_outline: str = "",
    references: list[str] | None = None,
    context_files: list[str] | None = None,
) -> str:
    client = await get_ds_client()
    if not client:
        return "Error: DeepSeek client not available"

    topic_line = f"《{topic_title}》" if topic_title else ""
    if topic_logic:
        topic_line += f"（{topic_logic}）"

    context = ""
    if context_files:
        for f in context_files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()[:4000]
                context += f"\n--- 素材 ---\n{content}\n"
            except Exception:
                pass

    # Build the prompt by substituting variables into skill's system_prompt.md
    # The new skill format uses {variable} placeholders
    context_block = context or "（无额外素材）"
    bs_block = brainstorm_outline or ""

    try:
        prompt = skill_content.format(
            constraint=constraint or "",
            target_length=target_length,
            topic_title=topic_title or "（由你自行确定主题）",
            topic_logic=topic_logic or "（由你自行展开逻辑）",
            topic_core_thesis=topic_core_thesis or "",
            topic_common_belief=topic_common_belief or "",
            topic_data_required=topic_data_required or "",
            topic_reader_hook=topic_reader_hook or "",
            topic_news_hook=topic_news_hook or "",
            topic_news_material=topic_news_material or "",
            brainstorm_block=bs_block,
            context_files=context_block,
        )
    except KeyError:
        # Fallback: old format skills that don't use {placeholders}
        prompt = f"""
{skill_content}

{bs_block}

【篇幅要求】: 目标篇幅约 {target_length} 字（±10%）。
【约束】: {constraint or "无特殊约束"}

【参考素材/选题】:
{context_block}

【当前确定的任务核心】: {topic_line}

请开始创作：
"""

    resp = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return resp.choices[0].message.content


async def run_wechat_pipeline(
    skill_content: str,
    raw_id: str,
    reports: list[dict],
    thesis: str = "",
    references: list[dict] | None = None,
    selected_chunks: list[dict] | None = None,
) -> dict:
    client = await get_ds_client()
    if not client:
        return {"error": "DeepSeek client not available"}

    references = references or []
    selected_chunks = selected_chunks or []

    # --- Node 1: Structured Data Extraction ---
    node1_parts = []
    for r in reports[:8]:
        path = r.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()[:6000]
            source = r.get("sourceLabel", r.get("sourceKey", ""))
            node1_parts.append(f"## {source}\n{text}")
        except Exception:
            pass

    # Add selected RAG chunks to Node 1 context
    for chunk in selected_chunks[:10]:
        snippet = chunk.get("snippet", "") or chunk.get("fullText", "")[:500]
        pipeline = chunk.get("pipelineLabel", chunk.get("pipeline", ""))
        node1_parts.append(f"## {pipeline}\n{snippet}")

    node1_prompt = f"""你是足球数据分析师。请从以下报告中提取结构化信息，输出 JSON。

输入报告：
{chr(10).join(node1_parts[:5])}

输出格式（JSON）：
{{"基本面":{{"主队":{{"近期战绩":"","核心伤病":"","赛程压力":"","攻防数据摘要":""}},"客队":{{"近期战绩":"","核心伤病":"","赛程压力":"","攻防数据摘要":""}}}},"数据信号":{{"关键发现":"","异常数据":"","趋势判断":""}},"数据盲区":"","核心看点":""}}
"""

    resp1 = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": node1_prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    node1 = resp1.choices[0].message.content

    # --- Node 2: Article Generation ---
    persona_line = _extract_wechat_persona(skill_content, raw_id)
    is_persona = _is_persona_skill(raw_id)

    # For persona skills, exclude odds reports
    if is_persona:
        reports = [r for r in reports if r.get("sourceKey") != "odds"]

    report_texts = []
    for r in reports[:5]:
        path = r.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                report_texts.append(f.read()[:8000])
        except Exception:
            pass

    ref_texts = ""
    for ref in references:
        path = ref.get("path", "")
        # Try as file path first; if not a valid file, treat path value as inline text content
        if not path:
            continue
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    ref_texts += f"\n--- 对标范文（请模仿其写作风格、语气、结构和用词习惯） ---\n{f.read()[:3000]}\n"
            else:
                ref_texts += f"\n--- 对标范文（请模仿其写作风格、语气、结构和用词习惯） ---\n{path[:3000]}\n"
        except Exception:
            pass

    node2_prompt = f"""{persona_line}

【写作规范】:
{skill_content}

{ref_texts}

【我的分析论点】: {thesis}

【结构化数据索引（用于快速查阅关键信息）】:
{node1}

【原始数据源（用于核实和引用具体数据）】:
{chr(10).join(report_texts[:3])}

请写一篇深度公众号文章，包含引言、技战术分析、数据深读、核心观点等部分。直接输出 markdown 正文。
"""

    resp2 = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": node2_prompt}],
        temperature=0.7,
    )
    node2 = resp2.choices[0].message.content

    # --- Node 3: Compliance Cleaning ---
    sw_map = load_sensitive_word_map()
    sw_table = "\n".join(f"- {k} → {v}" for k, v in list(sw_map.items())[:50])

    node3_prompt = f"""你是一个合规审查助手。请审查以下文章，使用提供的敏感词对照表替换其中的敏感词汇。

【敏感词对照表】:
{sw_table}

【待审查文章】:
{node2}

请直接输出替换后的完整文章，只替换敏感词汇，不要改变其他内容。
"""

    resp3 = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": node3_prompt}],
        temperature=0.1,
    )
    node3 = resp3.choices[0].message.content

    # Hard guarantee: apply CSV replacement
    node3 = apply_replacements(node3, sw_map)

    # --- Node 4: Format Cleaning ---
    node4 = _strip_markdown(node3)

    return {
        "nodeResults": {
            "node1": node1,
            "node2": node2,
            "node3": node3,
            "node4": node4,
        },
        "finalArticle": node4,
    }


async def run_wechat_pipeline_stream(
    skill_content: str,
    raw_id: str,
    reports: list[dict],
    thesis: str = "",
    references: list[dict] | None = None,
    selected_chunks: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream wechat pipeline via SSE — yields JSON event strings after each node."""
    client = await get_ds_client()
    if not client:
        yield json.dumps({"type": "error", "message": "DeepSeek client not available"})
        return

    references = references or []
    selected_chunks = selected_chunks or []

    yield json.dumps({"type": "progress", "node": 0, "label": "开始处理...", "total": 4})

    # --- Node 1 ---
    node1_parts = []
    for r in reports[:8]:
        path = r.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()[:6000]
            source = r.get("sourceLabel", r.get("sourceKey", ""))
            node1_parts.append(f"## {source}\n{text}")
        except Exception:
            pass

    for chunk in selected_chunks[:10]:
        snippet = chunk.get("snippet", "") or chunk.get("fullText", "")[:500]
        pipeline = chunk.get("pipelineLabel", chunk.get("pipeline", ""))
        node1_parts.append(f"## {pipeline}\n{snippet}")

    node1_prompt = f"""你是足球数据分析师。请从以下报告中提取结构化信息，输出 JSON。

输入报告：
{chr(10).join(node1_parts[:5])}

输出格式（JSON）：
{{"基本面":{{"主队":{{"近期战绩":"","核心伤病":"","赛程压力":"","攻防数据摘要":""}},"客队":{{"近期战绩":"","核心伤病":"","赛程压力":"","攻防数据摘要":""}}}},"数据信号":{{"关键发现":"","异常数据":"","趋势判断":""}},"数据盲区":"","核心看点":""}}
"""

    yield json.dumps({"type": "progress", "node": 1, "label": "Node 1/4: 结构化数据提取...", "total": 4})

    resp1 = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": node1_prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    node1 = resp1.choices[0].message.content
    yield json.dumps({"type": "node_complete", "node": 1, "label": "Node 1: 结构化数据提取", "output": node1})

    # --- Node 2 ---
    persona_line = _extract_wechat_persona(skill_content, raw_id)
    is_persona = _is_persona_skill(raw_id)

    if is_persona:
        reports = [r for r in reports if r.get("sourceKey") != "odds"]

    report_texts = []
    for r in reports[:5]:
        path = r.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                report_texts.append(f.read()[:8000])
        except Exception:
            pass

    ref_texts = ""
    for ref in references:
        path = ref.get("path", "")
        # Try as file path first; if not a valid file, treat path value as inline text content
        if not path:
            continue
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    ref_texts += f"\n--- 对标范文（请模仿其写作风格、语气、结构和用词习惯） ---\n{f.read()[:3000]}\n"
            else:
                ref_texts += f"\n--- 对标范文（请模仿其写作风格、语气、结构和用词习惯） ---\n{path[:3000]}\n"
        except Exception:
            pass

    node2_prompt = f"""{persona_line}

【写作规范】:
{skill_content}

{ref_texts}

【我的分析论点】: {thesis}

【结构化数据索引（用于快速查阅关键信息）】:
{node1}

【原始数据源（用于核实和引用具体数据）】:
{chr(10).join(report_texts[:3])}

请写一篇深度公众号文章，包含引言、技战术分析、数据深读、核心观点等部分。直接输出 markdown 正文。
"""

    yield json.dumps({"type": "progress", "node": 2, "label": "Node 2/4: 文章生成...", "total": 4})

    resp2 = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": node2_prompt}],
        temperature=0.7,
    )
    node2 = resp2.choices[0].message.content
    yield json.dumps({"type": "node_complete", "node": 2, "label": "Node 2: 文章生成", "output": node2})

    # --- Node 3 ---
    sw_map = load_sensitive_word_map()
    sw_table = "\n".join(f"- {k} → {v}" for k, v in list(sw_map.items())[:50])

    node3_prompt = f"""你是一个合规审查助手。请审查以下文章，使用提供的敏感词对照表替换其中的敏感词汇。

【敏感词对照表】:
{sw_table}

【待审查文章】:
{node2}

请直接输出替换后的完整文章，只替换敏感词汇，不要改变其他内容。
"""

    yield json.dumps({"type": "progress", "node": 3, "label": "Node 3/4: 合规清洗...", "total": 4})

    resp3 = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": node3_prompt}],
        temperature=0.1,
    )
    node3 = resp3.choices[0].message.content
    node3 = apply_replacements(node3, sw_map)
    yield json.dumps({"type": "node_complete", "node": 3, "label": "Node 3: 合规清洗", "output": node3})

    # --- Node 4 ---
    yield json.dumps({"type": "progress", "node": 4, "label": "Node 4/4: 格式清洗...", "total": 4})
    node4 = _strip_markdown(node3)
    yield json.dumps({"type": "node_complete", "node": 4, "label": "Node 4: 格式清洗", "output": node4})

    yield json.dumps({
        "type": "complete",
        "finalArticle": node4,
    })


async def convert_to_short_video(text: str) -> list[dict]:
    """Convert a copywriting output to short-video format with hooks and CTAs."""
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == "short-video-converter"), None)
    if not skill:
        raise RuntimeError("short-video-converter skill not found")

    client = await get_ds_client()
    if not client:
        raise RuntimeError("DeepSeek client not available")

    prompt = skill.content.replace("{constraint}", "")
    user_msg = f"请对以下文案做短视频结构包装：\n\n{text}"

    resp = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
    )
    raw = resp.choices[0].message.content

    # Parse the output into structured variants (tolerant regex)
    variants = []
    m_a = re.search(r"={3,}\s*VERSION_?A\s*={3,}\s*\n?(.*?)(?=\s*={3,}\s*VERSION_?B\s*=)", raw, re.DOTALL | re.IGNORECASE)
    m_b = re.search(r"={3,}\s*VERSION_?B\s*={3,}\s*\n?(.*?)(?=\s*={3,}\s*BODY\s*=)", raw, re.DOTALL | re.IGNORECASE)
    m_body = re.search(r"={3,}\s*BODY\s*={3,}\s*\n?(.*?)(?=\s*={3,}\s*CTA\s*=)", raw, re.DOTALL | re.IGNORECASE)
    m_cta = re.search(r"={3,}\s*CTA\s*={3,}\s*\n?(.*)", raw, re.DOTALL | re.IGNORECASE)

    body_text = m_body.group(1).strip() if m_body else text
    cta_text = m_cta.group(1).strip() if m_cta else ""

    if m_a:
        variants.append({
            "type": "version_a",
            "label": "数据冲击 / 反直觉",
            "hook": m_a.group(1).strip(),
            "body": body_text,
            "cta": cta_text,
        })
    if m_b:
        variants.append({
            "type": "version_b",
            "label": "悬念 / 观点前置",
            "hook": m_b.group(1).strip(),
            "body": body_text,
            "cta": cta_text,
        })

    # Fallback: if no structured sections found, return raw text as single variant
    if not variants:
        variants.append({
            "type": "raw",
            "label": "原始输出",
            "hook": raw[:500].strip(),
            "body": raw[500:].strip() if len(raw) > 500 else raw,
            "cta": "",
        })

    return variants
