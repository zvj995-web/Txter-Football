import re
import json
import asyncio
import unicodedata
from pathlib import Path
from datetime import datetime

from app.core.config import settings
from app.services.config_service import CONFIG_FILE, load_config, _default_conf
from app.models.misc import (
    BrainstormOutline, BrainstormOutlineDetail,
    ReferenceArticle, FileItem, SaveRequest, SaveResult,
)


# --- Brainstorm Outlines ---

BRAINSTORM_DIR = Path(settings.brainstorm_outlines_dir)

def list_brainstorm_outlines() -> list[BrainstormOutline]:
    if not BRAINSTORM_DIR.exists():
        return []
    results = []
    for f in sorted(BRAINSTORM_DIR.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue

        title_match = re.search(r"^#\s*(.+)", text)
        title = title_match.group(1).strip() if title_match else f.stem

        logic_match = re.search(r"##\s*🧩\s*核心逻辑\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        core_logic = ""
        if logic_match:
            lines = [l.strip(" -") for l in logic_match.group(1).strip().split("\n") if l.strip()]
            core_logic = "; ".join(lines[:3])

        compliance = ""
        redline = re.search(r"##\s*🛑\s*合规红线\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
        if redline:
            lines = [l.strip(" -") for l in redline.group(1).strip().split("\n") if l.strip()]
            compliance = "; ".join(lines[:3])

        results.append(BrainstormOutline(
            filename=f.name,
            title=title,
            coreLogic=core_logic,
            compliance=compliance,
        ))
    return results


def get_brainstorm_outline(filename: str) -> BrainstormOutlineDetail | None:
    file_path = BRAINSTORM_DIR / filename
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    return BrainstormOutlineDetail(filename=filename, content=content)


# --- Reference Articles ---

REFERENCE_DIR = Path(settings.reference_articles_dir)


def list_references(ip: str = "") -> list[ReferenceArticle]:
    results = []
    if not REFERENCE_DIR.exists():
        return results

    # IP-specific: persona/ or yssq/
    if ip:
        ip_dir = REFERENCE_DIR / ip
        dirs = [ip_dir] if ip_dir.exists() else []
    else:
        dirs = [d for d in REFERENCE_DIR.iterdir() if d.is_dir() or d.suffix in (".md", ".txt")]

    for d in dirs:
        if d.is_dir():
            for f in sorted(d.glob("*.{md,txt}"), key=lambda x: x.stat().st_mtime, reverse=True):
                results.append(ReferenceArticle(path=str(f), filename=f.name))
        elif d.is_file() and d.suffix in (".md", ".txt"):
            results.append(ReferenceArticle(path=str(d), filename=d.name))

    return results


# --- Files (general file browsing, like reports but raw) ---

SOURCE_LABELS = {
    "whoscored": "📊 whoscored", "api-football": "📋 api-football",
    "odds": "💰 odds", "inoreader": "📰 inoreader",
    "polymarket": "🗳️ polymarket", "djyy": "📡 djyy",
    "understat-pre": "📐 understat-pre", "understat-post": "📐 understat-post",
    "fotmob": "📱 fotmob", "grok-news": "🤖 grok-news",
    "grok-footballworld": "🌍 grok-footballworld",
}


def list_files(keyword: str = "") -> list[FileItem]:
    config = load_config()
    managed = config.get("managed_paths", {})
    results = []
    for source_key, dir_path in managed.items():
        d = Path(dir_path)
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if keyword and keyword.lower() not in f.name.lower():
                continue
            results.append(FileItem(
                path=str(f),
                filename=f.name,
                sourceKey=source_key,
                sourceLabel=SOURCE_LABELS.get(source_key, source_key),
            ))
    results.sort(key=lambda r: r.filename)
    return results


# --- Save ---

# Filename sanitization: ported from workbench for Windows / cloud-drive compatibility
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # 各类符号 & 象形
    "\U0001FA00-\U0001FAFF"
    "\U0001F600-\U0001F64F"  # emoticons
    "\U00002600-\U000026FF"  # 杂项符号
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F700-\U0001F77F"
    "‍️"           # zero-width joiner / variation selector-16
    "]+",
    flags=re.UNICODE,
)
_FILENAME_UNSAFE_RE = re.compile(
    r'[\\/:*?"<>|：＊？＂＜＞｜／＼'
    r'《》【】\[\]（）()「」『』'
    r'“”‘’'
    r"'\""  # ASCII quotes
    r'\n\r\t]+'
)


def _sanitize_for_filename(s: str, max_len: int = 40) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _EMOJI_RE.sub("", s)
    s = _FILENAME_UNSAFE_RE.sub("_", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._-")
    return s[:max_len].strip("._-") or ""


def _get_save_dir(folder: str, ip: str = "") -> Path:
    base = Path(settings.copywriting_output_root)
    if folder == "wechat":
        if ip == "persona" or ip == "转体":
            return Path(settings.wechat_draft_reserve_dir_persona)
        return Path(settings.wechat_draft_reserve_dir)
    elif folder == "polish":
        return base / "polish_output"
    else:
        if ip == "persona" or ip == "转体":
            return base / "转体世界波"
        elif ip == "yssq":
            return base / "通用文件夹"
        return base


async def save_file(req: SaveRequest) -> SaveResult:
    try:
        save_dir = _get_save_dir(req.folder, req.ip)
        save_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _sanitize_for_filename(req.filename) or "文案"
        file_path = save_dir / f"{ts}_{safe_name}.txt"

        # Anti-collision counter
        counter = 1
        while file_path.exists():
            file_path = save_dir / f"{ts}_{safe_name}_{counter}.txt"
            counter += 1

        # Build body with metadata headers (same format as workbench)
        header_lines = [
            f"# 生成时间：{ts}",
            f"# skillId：{req.skillId}",
        ]
        if req.folder:
            header_lines.append(f"# 来源：{req.folder}")
        if req.ip:
            header_lines.append(f"# IP：{req.ip}")

        body = req.content
        body_normalized = body.replace("\r\n", "\n").replace("\r", "\n")
        body_crlf = body_normalized.replace("\n", "\r\n")
        full = "\n".join(header_lines) + "\n\n" + body_crlf

        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(full)

        # Async GDrive upload (fire-and-forget, non-blocking)
        asyncio.create_task(_try_gdrive_upload(str(file_path), req.skillId))

        return SaveResult(success=True, savedPath=str(file_path))
    except Exception as e:
        return SaveResult(success=False, error=str(e))


async def _try_gdrive_upload(file_path: str, skill_id: str = ""):
    """Fire-and-forget GDrive upload if uploader module exists."""
    try:
        import sys
        wb = Path(settings.workbench_config).parent
        if str(wb) not in sys.path:
            sys.path.insert(0, str(wb))
        from txter_gdrive_uploader import upload_file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, upload_file, file_path, skill_id)
    except Exception:
        pass


# --- Config ---

def update_config(updates: dict) -> dict:
    saved = {}
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            saved = {}

    for key, value in updates.items():
        if key in _default_conf or key in ("managed_paths", "topic_library_paths", "style_translations"):
            saved[key] = value

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
    return load_config()
