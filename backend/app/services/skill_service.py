import re
import yaml
from pathlib import Path

from app.core.config import settings
from app.models.skills import SkillOut
from app.services.config_service import load_config

SKILLS_DIR = Path(settings.skills_dir)
if not SKILLS_DIR.is_absolute():
    SKILLS_DIR = (Path(__file__).parent.parent.parent / SKILLS_DIR).resolve()

LEGACY_SKILLS_DIR = Path(settings.legacy_skills_dir).expanduser()

IP_RULES = {
    "txter-persona-": "📽️ 转体世界波",
    "txter-football-yssq-": "🎯 弈神说球",
    "txter-football-": "🌐 通用足球风格",
}

WECHAT_TAG = "wechat-article"
TOPIC_TAG = "topic-generation"
COPYWRITING_TAG = "copywriting"

TYPE_TO_TAGS = {
    "wechat-article": [WECHAT_TAG],
    "topic-generation": [TOPIC_TAG],
    "copywriting": [COPYWRITING_TAG],
}


# --------------- new format: skills/{name}/manifest.yaml + system_prompt.md ---------------

def _load_new_skills() -> list[SkillOut]:
    """Load skills defined under the project's own skills/ directory."""
    result = []
    if not SKILLS_DIR.exists():
        return result

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        manifest_path = skill_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        raw_id = manifest.get("name", "")
        if not raw_id:
            continue

        tags = manifest.get("tags", [])
        skill_type = manifest.get("type", "")
        if skill_type in TYPE_TO_TAGS:
            for tag in TYPE_TO_TAGS[skill_type]:
                if tag not in tags:
                    tags.append(tag)

        # Read system prompt
        content = ""
        prompt_path = skill_dir / "system_prompt.md"
        if prompt_path.exists():
            try:
                content = prompt_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Determine IP
        ip = manifest.get("ip", "")
        if ip == "yssq":
            ip_display = "🎯 弈神说球"
        elif ip == "persona":
            ip_display = "📽️ 转体世界波"
        else:
            ip_display = "⚙️ 其他"

        display_name = manifest.get("title", raw_id)

        result.append(SkillOut(
            rawId=raw_id,
            name=display_name,
            description=manifest.get("description", ""),
            tags=tags,
            content=content,
            path=str(manifest_path),
            manifest=manifest,  # type: ignore — SkillOut supports extra fields via pydantic
        ))

    return result


# --------------- legacy format: ~/.hermes/skills/**/SKILL.md ---------------

def _parse_tags(content: str) -> list[str]:
    inline = re.search(r"tags:\s*\[(.*?)\]", content)
    if inline:
        return [t.strip().strip('"').strip("'") for t in inline.group(1).split(",") if t.strip()]
    block = re.search(r"tags:\s*\n((?:\s{2,}-\s*.+\n?)+)", content)
    if block:
        return [re.sub(r"^\s*-\s*", "", line).strip().strip('"').strip("'")
                for line in block.group(1).splitlines() if line.strip()]
    return []


def _load_legacy_skills(allowed_types: tuple = ()) -> list[SkillOut]:
    """Load legacy SKILL.md format skills. If allowed_types is provided, only return
    skills whose tags match at least one of those types (e.g. wechat-article only)."""
    config = load_config()
    translations = config.get("style_translations", {})

    result = []
    if not LEGACY_SKILLS_DIR.exists():
        return result

    for skill_path in sorted(LEGACY_SKILLS_DIR.glob("**/SKILL.md")):
        if '.archive' in str(skill_path).split('/'):
            continue
        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception:
            continue

        name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
        if not name_match:
            continue
        raw_id = name_match.group(1).strip()
        if not raw_id.startswith("txter-"):
            continue

        desc_match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else ""

        tags = _parse_tags(content)

        # Filter by allowed types
        if allowed_types:
            ok = any(t in tags for t in allowed_types)
            if not ok:
                continue

        # Determine IP
        ip = "⚙️ 其他"
        for prefix, ip_name in IP_RULES.items():
            if raw_id.startswith(prefix):
                ip = ip_name
                break

        # Build display name
        display_name = translations.get(raw_id)
        if not display_name:
            display_name = ip

        # If it has tags, use the first H1 as the display name
        title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        if title_match and (WECHAT_TAG in tags or TOPIC_TAG in tags):
            display_name = title_match.group(1).strip()

        result.append(SkillOut(
            rawId=raw_id,
            name=display_name,
            description=description,
            tags=tags,
            content=content,
            path=str(skill_path),
        ))

    return result


# --------------- unified loader ---------------

def load_all_skills() -> list[SkillOut]:
    """Load all skills: new format (skills/) + legacy wechat-article only from Hermes."""
    new_skills = _load_new_skills()
    new_ids = {s.rawId for s in new_skills}

    # From legacy, only load wechat-article — copywriting & topic-gen come from new format
    legacy_skills = _load_legacy_skills(allowed_types=(WECHAT_TAG,))
    legacy_skills = [s for s in legacy_skills if s.rawId not in new_ids]

    return new_skills + legacy_skills


def filter_by_type(skills: list[SkillOut], skill_type: str) -> list[SkillOut]:
    if skill_type == "wechat-article":
        return [s for s in skills if WECHAT_TAG in s.tags]
    elif skill_type == "topic-generation":
        return [s for s in skills if TOPIC_TAG in s.tags]
    elif skill_type == "copywriting":
        return [s for s in skills if COPYWRITING_TAG in s.tags]
    return skills
