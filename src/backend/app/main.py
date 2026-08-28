"""FastAPI app factory. Routers are mounted here as later tasks add them."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Neev API",
        version="0.1.0",
        description="Serves pipeline-shaped loan data to the Neev owner and bank consoles.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": get_settings().neev_mode}

    return app


app = create_app()
