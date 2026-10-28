from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    dashboard,
    leads,
    markets,
    reports,
    scans,
    settings,
    system,
    verticals,
)
from app.database.migrations import run_migrations
from app.database.migrations import verify_schema
from app.config.settings import get_settings
from app.api.security import InternalAuthenticationMiddleware
from app.api.routes import workflow, campaigns, intelligence, client_reports, deletions
from app.api.routes import sales,mail,tracking
from fastapi.responses import JSONResponse
from fastapi import Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure migrations are applied on server startup
    if get_settings().app_env == "production":
        verify_schema(minimum_version=4)
    else:
        run_migrations()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LeadEngine API",
        description="Zero-cost B2B Lead Discovery, Auditing & Qualification Application API",
        version="3.0.0",
        docs_url=None if get_settings().app_env == "production" else "/docs",
        redoc_url=None if get_settings().app_env == "production" else "/redoc",
        openapi_url=None if get_settings().app_env == "production" else "/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[] if get_settings().app_env == "production" else [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8787",
            "http://127.0.0.1:8787",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(InternalAuthenticationMiddleware)

    @app.exception_handler(Exception)
    async def sanitized_error(request: Request, exc: Exception):
        return JSONResponse({"detail": "The engine could not complete this request. Please retry."}, status_code=500)

    # Health check
    @app.get("/api/health", tags=["System"])
    def health_check():
        return {"status": "ok", "app": "LeadEngine", "version": "3.0.0"}

    # Include routers under /api
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(markets.router, prefix="/api")
    app.include_router(verticals.router, prefix="/api")
    app.include_router(scans.router, prefix="/api")
    app.include_router(leads.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(workflow.router, prefix="/api")
    app.include_router(sales.router, prefix='/api')
    app.include_router(mail.router, prefix='/api')
    app.include_router(tracking.router, prefix='/api')
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(intelligence.router, prefix="/api")

    app.include_router(client_reports.router, prefix="/api")
    app.include_router(deletions.router, prefix="/api")

    return app


app = create_app()
