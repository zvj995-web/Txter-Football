import csv
from pathlib import Path

from app.core.config import settings


def load_sensitive_word_map(csv_path: str = "") -> dict:
    p = Path(csv_path or settings.sensitive_words_csv).expanduser()
    if not p.exists():
        return {}
    mapping = {}
    for enc in ("utf-8", "gbk"):
        try:
            with open(p, "r", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        src = row[0].strip()
                        repl = row[1].strip()
                        if src:
                            mapping[src] = repl
            break
        except (UnicodeDecodeError, Exception):
            continue
    return mapping


def apply_replacements(text: str, mapping: dict) -> str:
    if not mapping:
        return text
    for src in sorted(mapping.keys(), key=len, reverse=True):
        text = text.replace(src, mapping[src])
    return text
