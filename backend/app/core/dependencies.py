import json
from pathlib import Path
from openai import AsyncOpenAI

from app.core.config import settings


def load_hermes_auth():
    path = Path(settings.hermes_auth_path).expanduser()
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_deepseek_credential():
    auth = load_hermes_auth()
    if not auth:
        return None, None
    pool = auth.get("credential_pool", {}).get("deepseek", [])
    if not pool:
        return None, None
    healthy = [c for c in pool if c.get("last_status") != "exhausted" and c.get("access_token")]
    chosen = (healthy or pool)[0]
    base = chosen.get("base_url") or "https://api.deepseek.com/v1"
    if not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return chosen.get("access_token"), base


def get_deepseek_async_client() -> AsyncOpenAI | None:
    key, base = get_deepseek_credential()
    if not key:
        return None
    return AsyncOpenAI(api_key=key, base_url=base)


_ds_client: AsyncOpenAI | None = None


async def get_ds_client() -> AsyncOpenAI | None:
    global _ds_client
    if _ds_client is None:
        _ds_client = get_deepseek_async_client()
    return _ds_client
