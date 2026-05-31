from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Paths
    hermes_auth_path: str = "~/.hermes/auth.json"
    skills_dir: str = "skills"       # new format skills (relative to project root)
    legacy_skills_dir: str = "~/.hermes/skills"  # old SKILL.md format (wechat-article only)
    workbench_config: str = "/home/ubuntu/projects/txter-workbench/config.json"
    sensitive_words_csv: str = "/home/ubuntu/projects/txter-workbench/sensitive_words.csv"
    topic_libraries_dir: str = "/home/ubuntu/projects/txter-workbench/topic_libraries"
    brainstorm_outlines_dir: str = "/home/ubuntu/projects/txter-workbench/BRAINSTORM_OUTLINES"
    reference_articles_dir: str = "/home/ubuntu/projects/txter-workbench/reference_articles"
    copywriting_output_root: str = "/home/ubuntu/projects/txter-workbench/copywriting_output"
    wechat_draft_reserve_dir: str = "/home/ubuntu/握手文件夹/弈神说球草稿箱/弈神说球草稿储备"
    wechat_draft_reserve_dir_persona: str = "/home/ubuntu/握手文件夹/转体世界波草稿箱/转体世界波草稿储备"

    # ChromaDB
    chroma_db_path: str = "/home/ubuntu/projects/football-rag/chroma_db"
    chroma_collection: str = "football_reports"
    team_map_path: str = "/home/ubuntu/projects/football-rag/team_map.json"

    # API keys
    gemini_api_key: str = ""
    grok_api_key: str = ""
    grok_model: str = "grok-4.3"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"]

    model_config = dict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
