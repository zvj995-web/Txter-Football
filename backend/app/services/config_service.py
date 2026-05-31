import json
from pathlib import Path

from app.core.config import settings

CONFIG_FILE = Path(settings.workbench_config)
LEGACY_GENERAL_LAB_ID = "txter-general-topic-lab"

_default_conf = {
    "managed_paths": {},
    "style_translations": {},
    "topic_library_paths": {},
    "sensitive_word_csv_path": str(Path(settings.sensitive_words_csv)),
    "reference_articles_path": str(Path(settings.reference_articles_dir)),
}


def load_config() -> dict:
    saved = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            saved = {}

    result = {}
    for key, default_val in _default_conf.items():
        result[key] = saved.get(key, default_val)

    # Backfill legacy
    legacy_central = CONFIG_FILE.parent / "CENTRAL_TOPIC_LIBRARY.md"
    tlp = result["topic_library_paths"]
    if LEGACY_GENERAL_LAB_ID not in tlp and legacy_central.exists():
        tlp[LEGACY_GENERAL_LAB_ID] = str(legacy_central)

    return result
