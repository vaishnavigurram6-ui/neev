"""FastAPI app factory and router mounting.

Nothing here imports `neev_pipeline`, `google-adk`, or any Google client. The
only path that would is `app.services.live_runner`, whose import is deferred
inside the runner factory and never executed while the dry run is active.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, boq, contractors, jobs, loans, portfolio, tranches
from app.core.settings import get_settings

# Three routers share the /api/loans prefix. That is safe because none of their
# paths overlap — `/{loan_id}` cannot swallow `/{loan_id}/boq/latest`, since
# Starlette matches whole paths rather than prefixes — so the order below is
# chosen for a readable OpenAPI document: auth, then the loan, then its
# analysis, then the bank's views.
ROUTERS = [
    auth.router,
    loans.router,
    boq.router,
    jobs.router,
    portfolio.router,
    tranches.router,
    contractors.router,
]


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

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()
