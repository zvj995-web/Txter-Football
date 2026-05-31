from pathlib import Path

from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import skills, reports, topics, generation, polish, rag, misc, news

FRONTEND_DIST = Path(__file__).parent.parent.parent.parent / "projects" / "txter-frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="txter API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes registered first — they take precedence over the catch-all
    app.include_router(skills.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(topics.router, prefix="/api")
    app.include_router(generation.router, prefix="/api")
    app.include_router(polish.router, prefix="/api")
    app.include_router(rag.router, prefix="/api")
    app.include_router(misc.router, prefix="/api")
    app.include_router(news.router, prefix="/api")

    # Serve built frontend static files (fast through SSH tunnel)
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def serve_spa(path: str):
            file_path = FRONTEND_DIST / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

        @app.get("/", include_in_schema=False)
        async def serve_root():
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
