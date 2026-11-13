"""
FastAPI Main Application Entrypoint.
Adheres to fastapi.md standards.
"""

import os
# Prevent Windows Application Control / AppLocker blocking on compiled Cython extensions
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from backend.core.config import settings
# pyrefly: ignore [missing-import]
from backend.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-create all DB tables on startup."""
    try:
        # pyrefly: ignore [missing-import]
        from sqlalchemy import text
        # pyrefly: ignore [missing-import]
        from backend.dependencies.database import _init_engine
        # pyrefly: ignore [missing-import]
        from backend.models.base import Base
        # Import all models to register them with Base.metadata
        import backend.models  # noqa
        engine = await _init_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Idempotent column migrations for SQLite
            for col_sql in [
                "ALTER TABLE interview_sessions ADD COLUMN coaching_mode VARCHAR(50) DEFAULT 'COACHING'",
                "ALTER TABLE questions ADD COLUMN stage_name VARCHAR(100) DEFAULT 'Foundational Orientation'",
                "ALTER TABLE questions ADD COLUMN stage_index INTEGER DEFAULT 1",
                "ALTER TABLE questions ADD COLUMN coach_lead_in TEXT",
                "ALTER TABLE evaluations ADD COLUMN exemplar_answer TEXT",
                "ALTER TABLE evaluations ADD COLUMN coach_note TEXT",
            ]:
                try:
                    await conn.execute(text(col_sql))
                except Exception:
                    pass
        print("[OK] Database tables and coach schemas created/verified.")
    except Exception as e:
        print(f"[WARN] DB table creation skipped: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
