"""FastAPI application entry point."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from idatenops import __version__
from idatenops.api.routes import dev_router, router
from idatenops.api.lead_recovery_routes import (
    router as lead_recovery_router,
)

load_dotenv()

app = FastAPI(
    title="IdatenOps API",
    summary="AI-assisted workspace for pre-owned automotive retail",
    version=__version__,
    description=(
        "Local MVP scaffold. The development policy-check endpoint evaluates "
        "snapshots only and never creates a booking."
    ),
)
app.include_router(router)
app.include_router(lead_recovery_router)

app_env = os.getenv("APP_ENV", "local").strip().lower()
include_dev_routes = os.getenv("IDATENOPS_ENABLE_DEV_ENDPOINTS", "true").strip().lower() == "true"
if app_env != "production" and include_dev_routes:
    app.include_router(dev_router)
