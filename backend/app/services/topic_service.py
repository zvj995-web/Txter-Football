import re
import random
import shutil
from datetime import datetime
from pathlib import Path


from app.core.config import settings
from app.core.dependencies import get_ds_client
from app.services.config_service import load_config
from app.services.skill_service import load_all_skills, TOPIC_TAG
from app.models.topics import TopicOut, TopicLibraryOut, TopicAppendRequest, TopicRefineRequest

TOPIC_LIBRARIES_DIR = Path(settings.topic_libraries_dir)
FALLBACK_DIMENSION_KEY = "待开发"

LIBRARY_SECTION_RE = re.compile(r"^##\s+(.+)$")
LIBRARY_TOPIC_RE = re.compile(r"^\s*(\d+)\.\s*\*\*《(.+?)》\*\*")
LIBRARY_FIELD_RE = re.compile(r"^\s*-\s*\*\*(.+?)\*\*[：:]\s*(.+)$")
LIBRARY_LOGIC_RE = re.compile(r"\*\*(?:核心)?逻辑\*\*[：:]\s*(.+)$")
LIBRARY_FACT_RE = re.compile(r"^\s*[•・]\s*(.+)$")

FIELD_LABEL_MAP = {
    "核心论点": "core_thesis",
    "逻辑": "logic",
    "认知误区": "common_belief",
    "信息差": "insider_knowledge",
    "逻辑链": "logic_chain",
    "所需素材": "data_required",
    "难度": "difficulty",
    "AI工具类型": "ai_tool_type",
    "生活化类比": "life_analogy",
    "流量钩子": "reader_hook",
    "逻辑模型": "logic_model",
    "新闻素材": "news_summary",
    "与选题关联": "news_relevance",
}

_CHINESE_NUMERALS = "一二三四五六七八九十百千"
_DIM_DELIMS = r"\s：:（()\[\]（）/、|"
_DIM_INDEX_PATTERN = re.compile(
    rf"^维度\s*[{_CHINESE_NUMERALS}\d]+\s*[：:]\s*([^{_DIM_DELIMS}]+)"
)
_DIM_HEAD_PATTERN = re.compile(rf"^([^{_DIM_DELIMS}]+)")

DEFAULT_LIBRARY_TEMPLATE = """# ✍️ {display_name} 选题库 ({raw_id})

> **同步说明**：本文件由 `{raw_id}` 技能独占维护。

---

## 💡 待开发：灵感池
*尚未分类的选题先落在这里。*

---
"""


def extract_dimension_key(heading: str) -> str:
    if not heading:
        return ""
    stripped = re.sub(r"^\W+", "", heading).strip()
    m = _DIM_INDEX_PATTERN.match(stripped)
    if m:
        return m.group(1).strip()
    m = _DIM_HEAD_PATTERN.match(stripped)
    if m:
        return m.group(1).strip()
    return stripped


def get_library_path_for_skill(raw_id: str) -> Path:
    config = load_config()
    override = config.get("topic_library_paths", {}).get(raw_id)
    if override:
        return Path(override).expanduser()
    return TOPIC_LIBRARIES_DIR / f"{raw_id}.md"


def ensure_library_exists(path: Path, raw_id: str, display_name: str):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    content = DEFAULT_LIBRARY_TEMPLATE.format(display_name=display_name, raw_id=raw_id)
    path.write_text(content, encoding="utf-8")


def parse_topic_library(path: Path) -> dict:
    sections = {}
    if not path.exists():
        return sections
    text = path.read_text(encoding="utf-8")
    current_heading = None
    current_topic = None
    for line in text.split("\n"):
        h = LIBRARY_SECTION_RE.match(line)
        if h:
            current_heading = h.group(1).strip()
            sections.setdefault(current_heading, [])
            current_topic = None
            continue
        if current_heading is None:
            continue
        t = LIBRARY_TOPIC_RE.match(line)
        if t:
            current_topic = {
                "number": int(t.group(1)),
                "title": t.group(2).strip(),
                "logic": "",
                "key_facts": [],
            }
            sections[current_heading].append(current_topic)
            continue
        if current_topic is None:
            continue
        f = LIBRARY_FIELD_RE.match(line)
        if f:
            label = f.group(1).strip()
            value = f.group(2).strip()
            field = FIELD_LABEL_MAP.get(label)
            if field:
                current_topic[field] = value
            if label in ("逻辑", "核心逻辑"):
                current_topic["logic"] = value
            continue
        l = LIBRARY_LOGIC_RE.search(line)
        if l:
            current_topic["logic"] = l.group(1).strip()
            continue
        fact = LIBRARY_FACT_RE.match(line)
        if fact:
            current_topic.setdefault("key_facts", []).append(fact.group(1).strip())
    return sections


def extract_dimension_keys(path: Path) -> tuple[list[str], list[str]]:
    sections = parse_topic_library(path)
    seen = []
    for heading in sections.keys():
        key = extract_dimension_key(heading)
        if key and key not in seen:
            seen.append(key)
    focus = [k for k in seen if k != FALLBACK_DIMENSION_KEY]
    return focus, seen


def get_library(skill_id: str) -> TopicLibraryOut | None:
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == skill_id and TOPIC_TAG in s.tags), None)
    if not skill:
        return None

    lib_path = get_library_path_for_skill(skill_id)
    ensure_library_exists(lib_path, skill_id, skill.name)
    sections = parse_topic_library(lib_path)
    focus_keys, all_keys = extract_dimension_keys(lib_path)

    topics = []
    for heading, items in sections.items():
        dim_key = extract_dimension_key(heading)
        for item in items:
            topics.append(TopicOut(
                title=item.get("title", ""),
                logic=item.get("logic", ""),
                dimension=dim_key,
                style=item.get("style", ""),
                audience=item.get("audience", ""),
                format=item.get("format", ""),
                duration=item.get("duration", ""),
                compliance=item.get("compliance", ""),
                core_thesis=item.get("core_thesis", ""),
                common_belief=item.get("common_belief", ""),
                data_required=item.get("data_required", ""),
                reader_hook=item.get("reader_hook", ""),
                logic_model=item.get("logic_model", ""),
                difficulty=item.get("difficulty", ""),
                hard_number=item.get("hard_number", ""),
                news_hook=item.get("news_hook", ""),
                news_material=item.get("news_material", ""),
                insider_knowledge=item.get("insider_knowledge", ""),
                logic_chain=item.get("logic_chain", ""),
                ai_tool_type=item.get("ai_tool_type", ""),
                life_analogy=item.get("life_analogy", ""),
                news_summary=item.get("news_summary", ""),
                news_relevance=item.get("news_relevance", ""),
            ))

    return TopicLibraryOut(
        skillId=skill_id,
        skillName=skill.name,
        dimensions=focus_keys,
        topics=topics,
    )


def list_all_libraries() -> list[TopicLibraryOut]:
    all_skills = load_all_skills()
    topic_skills = [s for s in all_skills if TOPIC_TAG in s.tags]
    result = []
    for skill in topic_skills:
        lib = get_library(skill.rawId)
        if lib:
            result.append(lib)
    return result


def get_random_topic(skill_id: str) -> TopicOut | None:
    lib = get_library(skill_id)
    if not lib or not lib.topics:
        return None
    return random.choice(lib.topics)


def _backup_file(file_path: Path) -> Path | None:
    """Create a timestamped backup. Returns backup path or None."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = file_path.parent / f"{file_path.name}.bak-{ts}"
    try:
        shutil.copy(file_path, backup)
        return backup
    except Exception:
        return None


def add_dimension(skill_id: str, dimension_name: str, description: str = "") -> TopicLibraryOut:
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == skill_id and TOPIC_TAG in s.tags), None)
    if not skill:
        raise ValueError(f"Skill not found: {skill_id}")

    lib_path = get_library_path_for_skill(skill_id)
    ensure_library_exists(lib_path, skill_id, skill.name)

    if not dimension_name or not dimension_name.strip():
        raise ValueError("维度名不能为空")

    heading_text = f"💡 {dimension_name.strip()}"
    new_key = extract_dimension_key(heading_text)
    if not new_key:
        raise ValueError("无法从输入中提取有效的维度短名")

    # Dedup check
    text = lib_path.read_text(encoding="utf-8")
    existing_keys = []
    fallback_idx = None
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = LIBRARY_SECTION_RE.match(line)
        if m:
            key = extract_dimension_key(m.group(1))
            existing_keys.append(key)
            if fallback_idx is None and key == FALLBACK_DIMENSION_KEY:
                fallback_idx = i

    if new_key in existing_keys:
        raise ValueError(f"维度「{new_key}」已存在，未重复追加")

    # Backup
    backup_path = _backup_file(lib_path)

    # Build section block
    block = [f"## {heading_text}"]
    desc_clean = (description or "").strip()
    if desc_clean:
        block.append(f"*{desc_clean}*")
    block.append("")
    block.append("---")
    block.append("")

    try:
        if fallback_idx is not None:
            new_lines = lines[:fallback_idx] + block + lines[fallback_idx:]
        else:
            tail = list(lines)
            while tail and tail[-1].strip() == "":
                tail.pop()
            tail.extend(["", "---", ""])
            new_lines = tail + block
        lib_path.write_text("\n".join(new_lines), encoding="utf-8")
        return get_library(skill_id)
    except Exception as e:
        if backup_path:
            try:
                shutil.copy(backup_path, lib_path)
            except Exception:
                pass
        raise RuntimeError(f"写入失败已回滚：{e}")


def append_topic(req: TopicAppendRequest) -> TopicLibraryOut:
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == req.skillId and TOPIC_TAG in s.tags), None)
    if not skill:
        raise ValueError(f"Skill not found: {req.skillId}")

    lib_path = get_library_path_for_skill(req.skillId)
    ensure_library_exists(lib_path, req.skillId, skill.name)

    content = lib_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    dim_heading = req.dimension if req.dimension else FALLBACK_DIMENSION_KEY

    # Find section boundaries
    section_starts = []
    for idx, line in enumerate(lines):
        m = LIBRARY_SECTION_RE.match(line)
        if m:
            section_starts.append((m.group(1).strip(), idx))
    if not section_starts:
        raise ValueError("选题库格式异常：找不到任何 ## 标题")

    section_ranges = []
    for i, (heading, start_idx) in enumerate(section_starts):
        end_idx = section_starts[i + 1][1] if i + 1 < len(section_starts) else len(lines)
        section_ranges.append({"heading": heading, "start": start_idx, "end": end_idx})

    # Find the target section (fuzzy match)
    headings_list = [s["heading"] for s in section_ranges]
    target_heading = None
    target_section_idx = None
    for i, h in enumerate(headings_list):
        if dim_heading in h or h in dim_heading:
            target_heading = h
            target_section_idx = i
            break
    if target_heading is None:
        # Fallback to "待开发" or last section
        for i, h in enumerate(headings_list):
            if FALLBACK_DIMENSION_KEY in h or "灵感" in h:
                target_heading = h
                target_section_idx = i
                break
        if target_heading is None:
            target_heading = headings_list[-1]
            target_section_idx = len(headings_list) - 1

    # Calculate next number (global)
    all_nums = []
    for line in lines:
        m = LIBRARY_TOPIC_RE.match(line)
        if m:
            all_nums.append(int(m.group(1)))
    next_num = max(all_nums) + 1 if all_nums else 1

    # Build topic entry
    topic_lines = [f"\n{next_num}. **《{req.title}》**"]
    if req.logic:
        topic_lines.append(f"   - **逻辑**：{req.logic}")
    if req.style:
        topic_lines.append(f"   - **风格**：{req.style}")
    if req.audience:
        topic_lines.append(f"   - **目标受众**：{req.audience}")
    if req.format:
        topic_lines.append(f"   - **呈现形式**：{req.format}")
    if req.duration:
        topic_lines.append(f"   - **时长**：{req.duration}")
    if req.compliance:
        topic_lines.append(f"   - **合规**：{req.compliance}")

    topic_text = "\n".join(topic_lines)

    # Backup
    backup_path = _backup_file(lib_path)

    try:
        section = section_ranges[target_section_idx]
        section_content = lines[section["start"]:section["end"]]
        # Find insert point: after last numbered topic, before trailing blank/separator lines
        insert_at = len(section_content)
        while insert_at > 1:
            cand = section_content[insert_at - 1].strip()
            if cand == "" or cand == "---":
                insert_at -= 1
            else:
                break
        section_content[insert_at:insert_at] = topic_lines

        new_lines = lines[:section["start"]] + section_content + lines[section["end"]:]
        lib_path.write_text("\n".join(new_lines), encoding="utf-8")
        return get_library(req.skillId)
    except Exception as e:
        if backup_path:
            try:
                shutil.copy(backup_path, lib_path)
            except Exception:
                pass
        raise RuntimeError(f"写入失败已回滚：{e}")


async def generate_candidates(
    skill_id: str, dimension: str = "", news_material: str = "", brainstorm: str = "", count: int = 5
) -> list[TopicOut]:
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == skill_id and TOPIC_TAG in s.tags), None)
    if not skill:
        raise ValueError(f"Skill not found: {skill_id}")

    client = await get_ds_client()
    if not client:
        raise RuntimeError("DeepSeek client not available")

    lib = get_library(skill_id)
    existing_titles = [t.title for t in (lib.topics if lib else [])] if lib else []
    existing_dims = lib.dimensions if lib else []

    mode = "B: 新闻驱动" if news_material else ("头脑风暴" if brainstorm else "A: 自主生长")
    dim_context = f"\n当前已有维度：{', '.join(existing_dims[:10])}" if existing_dims else ""
    dim_target = f"\n【聚焦主题】所有选题必须紧密围绕「{dimension}」展开，角度、数据、案例都直接关联，禁止生成无关选题。" if dimension else ""
    titles_context = f"\n已有选题（请勿重复）：{', '.join(existing_titles[:20])}" if existing_titles else ""
    brainstorm_context = f"\n【头脑风暴大纲】\n{brainstorm[:3000]}" if brainstorm else ""

    prompt = f"""{skill.content}

【生成模式】{mode}
{dim_context}{dim_target}{titles_context}{brainstorm_context}

【素材】（仅 B 模式有效）
{news_material or '（无新闻素材，自主生长模式）'}

请严格按照上述技能提示中的输出格式，生成 {count} 个候选选题的 JSON 数组。只输出 JSON 数组，不要任何解释。"""

    resp = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content

    try:
        import json
        data = json.loads(raw)
        items = data if isinstance(data, list) else data.get("topics", data.get("items", []))
        return [
            TopicOut(
                title=item.get("title", ""),
                logic=item.get("logic", ""),
                dimension=item.get("dimension", dimension),
                style=item.get("style", ""),
                audience=item.get("audience", ""),
                format=item.get("format", ""),
                duration=item.get("duration", ""),
                compliance=item.get("compliance", ""),
                core_thesis=item.get("core_thesis", ""),
                common_belief=item.get("common_belief", ""),
                data_required=item.get("data_required", ""),
                reader_hook=item.get("reader_hook", ""),
                logic_model=item.get("logic_model", ""),
                difficulty=item.get("difficulty", ""),
                hard_number=item.get("hard_number", ""),
                news_hook=item.get("news_hook", ""),
                news_material=news_material,
                insider_knowledge=item.get("insider_knowledge", ""),
                logic_chain=item.get("logic_chain", ""),
                ai_tool_type=item.get("ai_tool_type", ""),
                life_analogy=item.get("life_analogy", ""),
                news_summary=item.get("news_summary", ""),
                news_relevance=item.get("news_relevance", ""),
            )
            for item in items
        ]
    except Exception:
        return []


async def refine_topic(req: TopicRefineRequest) -> TopicOut:
    all_skills = load_all_skills()
    skill = next((s for s in all_skills if s.rawId == req.skillId and TOPIC_TAG in s.tags), None)
    if not skill:
        raise ValueError(f"Skill not found: {req.skillId}")

    client = await get_ds_client()
    if not client:
        raise RuntimeError("DeepSeek client not available")

    topic = req.topic
    prompt = f"""你是一位足球内容策略专家。当前技能：{skill.name}

一位用户对以下候选选题提出了修改意见，请根据反馈优化选题。

【原选题】
- 标题：{topic.get('title', '')}
- 逻辑：{topic.get('logic', '')}
- 维度：{topic.get('dimension', '')}
- 风格：{topic.get('style', '')}
- 受众：{topic.get('audience', '')}
- 形式：{topic.get('format', '')}
- 时长：{topic.get('duration', '')}
- 合规：{topic.get('compliance', '')}

【用户修改意见】
{req.feedback}

请输出优化后的选题 JSON：
{{"title": "...", "logic": "...", "dimension": "...", "style": "...", "audience": "...", "format": "...", "duration": "...", "compliance": "..."}}

要求：
- 保留用户满意的地方，针对性优化用户提出的问题
- 如果用户提供了新的角度或方向，融入选题
- 保持原有的 JSON 字段结构
- 只输出 JSON 对象，不要任何解释。"""

    resp = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content

    try:
        import json
        data = json.loads(raw)
        return TopicOut(
            title=data.get("title", ""),
            logic=data.get("logic", ""),
            dimension=data.get("dimension", topic.get("dimension", "")),
            style=data.get("style", ""),
            audience=data.get("audience", ""),
            format=data.get("format", ""),
            duration=data.get("duration", ""),
            compliance=data.get("compliance", ""),
        )
    except Exception:
        raise RuntimeError("Failed to parse refined topic")

