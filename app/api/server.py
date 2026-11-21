from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.migrations import run_migrations
from app.database.migrations import verify_schema
from app.config.settings import get_settings
from app.api.security import InternalAuthenticationMiddleware
from app.api.routes import organizations, foundation, system, workflow, tracking
from fastapi.responses import JSONResponse
from fastapi import Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure migrations are applied on server startup
    if get_settings().app_env == "production":
        verify_schema()
    else:
        run_migrations()
    from app.developer.mcp_server import build
    mcp,mcp_app=build();app.state.lead_mcp_mount.app=mcp_app
    import asyncio,os
    from contextlib import suppress
    task=None
    radar_task=None
    mail_task=None
    if get_settings().database_background_polling_enabled and get_settings().transactional_mail_enabled and get_settings().app_env!='test':
        from app.notifications.dispatch import loop as mail_loop
        mail_task=asyncio.create_task(mail_loop())
    if get_settings().database_background_polling_enabled and get_settings().intent_radar_schedules_enabled and get_settings().app_env!='test':
        from app.intent_radar.schedules import loop
        radar_task=asyncio.create_task(loop())
    if get_settings().heysow_webhooks_enabled and get_settings().app_env=='development' and os.environ.get('HEYSOW_LOCAL_PREVIEW')=='true':
        from app.webhooks.dispatch import preview_loop
        task=asyncio.create_task(preview_loop())
    try:
        async with mcp.session_manager.run():yield
    finally:
        if mail_task:
            mail_task.cancel()
            with suppress(asyncio.CancelledError):await mail_task
        if radar_task:
            radar_task.cancel()
            with suppress(asyncio.CancelledError):await radar_task
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):await task
            from app.webhooks.dispatch import shutdown
            await shutdown()
        from app.integrations.sheet_exports import shutdown as shutdown_exports
        await shutdown_exports()
    from app.api.read_cache import read_cache
    await read_cache.close()
    from app.database.postgres import close_pools
    close_pools()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PlaneByte Intent Radar API",
        description="Workspace-scoped intent research and platform services",
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
    from app.api.permissions import AuditCompletionMiddleware
    app.add_middleware(AuditCompletionMiddleware)

    @app.exception_handler(Exception)
    async def sanitized_error(request: Request, exc: Exception):
        return JSONResponse({"detail": "The engine could not complete this request. Please retry."}, status_code=500)

    from fastapi.exceptions import RequestValidationError
    from fastapi.exception_handlers import request_validation_exception_handler
    @app.exception_handler(RequestValidationError)
    async def safe_validation(request: Request, exc: RequestValidationError):
        from app.api.routes.accounts import PREFIX
        if request.url.path.startswith(PREFIX) or request.url.path=='/api/organization/admission/google':
            # Pydantic SecretStr does not redact FastAPI's input field by itself.
            # Never echo password, OTP, token, provider claim or input context.
            return JSONResponse({'detail':'Check the account details and try again.'},status_code=422,headers={'Cache-Control':'private, no-store'})
        return await request_validation_exception_handler(request,exc)

    # Health check
    @app.get("/api/health", tags=["System"])
    def health_check():
        return {"status": "ok", "app": "LeadEngine", "version": "3.0.0"}

    # The deployed Radar database does not contain the old product tables. Do
    # not register legacy handlers in this runtime (including its OpenAPI).
    # Local legacy-profile clients still have a separately tested contract.
    if get_settings().database_schema_profile != 'intent-radar-v1':
        from app.api.routes import (acquisition, assistant, automation, campaigns,
            client_reports, dashboard, deletions, discovery_searches, experiments,
            intelligence, leads, mail, markets, operations, people, qualification,
            reports, sales, scans, settings, tasks, verticals, workflows)
        for legacy in (workflow, acquisition, assistant, automation, campaigns, client_reports,
                       dashboard, deletions, discovery_searches, experiments,
                       intelligence, leads, mail, markets, operations, people,
                       qualification, reports, sales, scans, settings, tasks,
                       verticals, workflows):
            app.include_router(legacy.router,prefix='/api')

    app.include_router(foundation.router,prefix="/api")
    from app.api.routes import intelligence_jobs
    app.include_router(intelligence_jobs.router,prefix="/api")
    from app.api.routes import intent_radar
    app.include_router(intent_radar.router,prefix='/api')
    from app.api.routes import growth_intelligence
    app.include_router(growth_intelligence.router,prefix='/api')
    from app.api.routes import billing
    app.include_router(billing.router,prefix='/api')
    from app.api.routes import fixed_term_billing
    app.include_router(fixed_term_billing.router,prefix='/api')
    from app.api.routes import subscriptions
    app.include_router(subscriptions.router,prefix='/api')
    app.include_router(organizations.router,prefix="/api")
    from app.api.routes import admission
    app.include_router(admission.router,prefix='/api')
    from app.api.routes import accounts
    app.include_router(accounts.router,prefix='/api')
    from app.api.routes import transactional
    app.include_router(transactional.router,prefix='/api')
    from app.api.routes import icp
    app.include_router(icp.router,prefix="/api")
    from app.api.routes import onboarding
    app.include_router(onboarding.router,prefix="/api")
    from app.api.routes import domains
    app.include_router(domains.router,prefix="/api")
    from app.api.routes import company_discovery
    app.include_router(company_discovery.router,prefix="/api")
    from app.api.routes import integrations
    app.include_router(integrations.router,prefix="/api")
    from app.api.routes import radar_sheets
    app.include_router(radar_sheets.router,prefix='/api')
    from app.api.routes import radar_crm
    app.include_router(radar_crm.router,prefix='/api')
    from app.api.routes import account_profile
    app.include_router(account_profile.router,prefix="/api")
    from app.api.routes import developer,public_v1
    app.include_router(developer.router,prefix="/api")
    app.include_router(public_v1.router,prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(workflow.users_router, prefix="/api")
    from app.api.routes import webhooks
    app.include_router(webhooks.router,prefix="/api")
    from app.api.routes import help as product_help
    app.include_router(product_help.router,prefix="/api")
    from app.api.routes import search as workspace_search
    app.include_router(workspace_search.router,prefix="/api")
    app.include_router(tracking.router, prefix='/api')


    from app.developer.mcp_server import MountedMCP
    mounted=MountedMCP();app.state.lead_mcp_mount=mounted
    app.mount('/api/v1',mounted)
    return app


app = create_app()
