import os
import time
from pathlib import Path

from app.services.config_service import load_config
from app.models.reports import ReportOut

SOURCE_LABELS = {
    "whoscored": "📊 whoscored",
    "api-football": "📋 api-football",
    "odds": "💰 odds",
    "polymarket": "🗳️ polymarket",
    "djyy": "📡 djyy",
    "understat-pre": "📐 understat-pre",
    "understat-post": "📐 understat-post",
    "fotmob": "📱 fotmob",
}


def list_reports(keyword: str = "", from_hours: float | None = None, to_hours: float | None = None) -> list[ReportOut]:
    config = load_config()
    managed = config.get("managed_paths", {})
    results = []

    # Split into tokens: support spaces, newlines, commas as delimiters
    raw = keyword.strip()
    tokens = [t for t in raw.replace("\n", " ").replace(",", " ").split(" ") if t] if raw else []

    now = time.time()
    from_ts = now + (from_hours * 3600) if from_hours is not None else None
    to_ts = now + (to_hours * 3600) if to_hours is not None else None

    for source_key, dir_path in managed.items():
        d = Path(dir_path)
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            filename = f.name

            # Multi-keyword AND match against filename (case-insensitive)
            if tokens:
                fname_lower = filename.lower()
                if not all(t.lower() in fname_lower for t in tokens):
                    continue

            mtime = os.path.getmtime(str(f))
            mtime_ms = mtime * 1000

            # Time range filter (mtime is file modification time)
            if from_ts is not None and mtime < from_ts:
                continue
            if to_ts is not None and mtime > to_ts:
                continue

            results.append(ReportOut(
                path=str(f),
                sourceKey=source_key,
                sourceLabel=SOURCE_LABELS.get(source_key, source_key),
                filename=filename,
                mtime=mtime_ms,
            ))

    results.sort(key=lambda r: r.mtime, reverse=True)
    return results
