from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.internal import health, routing as routing_admin
from app.api.v1 import chat, models
from app.core.config import get_settings
from app.core.exceptions import RoutingBrainError, routing_brain_exception_handler
from app.core.logging import configure_logging, get_logger
from app.middleware.auth import AuthMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.providers.registry import ProviderRegistry
from app.routing.engine import RoutingEngine
from app.routing.policy import PolicyEngine
from app.routing.routing_brain import RoutingBrain
from app.routing.virtual_models import VirtualModelRegistry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info("startup", env=settings.app_env)

    # Initialize components
    virtual_registry = VirtualModelRegistry(settings.models_config_path)
    provider_registry = ProviderRegistry(settings)
    policy_engine = PolicyEngine(settings.routing_policies_dir, virtual_registry=virtual_registry)
    routing_brain = RoutingBrain(settings)
    routing_engine = RoutingEngine(routing_brain, policy_engine, provider_registry)

    # Store on app state for dependency injection
    app.state.settings = settings
    app.state.virtual_registry = virtual_registry
    app.state.provider_registry = provider_registry
    app.state.policy_engine = policy_engine
    app.state.routing_brain = routing_brain
    app.state.routing_engine = routing_engine

    logger.info(
        "components_ready",
        providers=provider_registry.available_providers(),
        departments=policy_engine.list_departments(),
    )

    yield

    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RoutingBrain",
        description="Intelligent LLM Routing Platform — OpenAI-compatible proxy",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # CORS — allow the frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Routing-Model", "X-Routing-Provider",
                        "X-Task-Type", "X-Complexity"],
    )

    # Auth middleware (dev mode: skip auth when no keys configured)
    app.add_middleware(
        AuthMiddleware,
        valid_api_keys=settings.api_keys_list,
        dev_mode=settings.is_development,
    )

    # Request ID middleware
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    app.add_exception_handler(RoutingBrainError, routing_brain_exception_handler)

    # Routes — OpenAI-compatible
    app.include_router(chat.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")

    # Routes — Internal admin
    app.include_router(health.router)
    app.include_router(health.router, prefix="/internal")
    app.include_router(routing_admin.router, prefix="/internal")

    return app


app = create_app()
