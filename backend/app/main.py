import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database.session import engine, Base
from app.database.seed import seed_database
from app.database.migrate import migrate_database
from app.api import categories, rules, scans, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event: initialize database schema, apply additive migrations, and ensure initial seed data."""
    Base.metadata.create_all(bind=engine)
    migrate_database()
    seed_database()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Explainable, uncertainty-aware compliance assistance API for packaged commodities under Indian Legal Metrology regulations.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded images directory for thumbnail/visual inspection
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register API Routers
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(scans.router, prefix=settings.API_V1_STR)
app.include_router(rules.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "framework": settings.DEFAULT_LEGAL_FRAMEWORK,
        "rule_version": settings.DEFAULT_RULE_VERSION,
        "legal_disclaimer": "Prototype compliance-assistance system. Not a substitute for statutory Metrology Officer verification."
    }
