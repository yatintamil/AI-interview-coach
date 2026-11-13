"""
Database Session Dependency Injection with resilient PostgreSQL connection testing
and single-connection StaticPool SQLite fallback.
"""

from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from backend.core.config import settings

logger = logging.getLogger(__name__)

_engine = None
_AsyncSessionLocal = None
_engine_initialized = False

SQLITE_FALLBACK_URL = "sqlite+aiosqlite:///./ai_interview_coach.db"


async def _migrate_sqlite_columns(conn):
    """Ensures newly added columns are present in existing SQLite tables."""
    try:
        table_columns = {
            "candidates": [
                ("password_hash", "VARCHAR(255)"),
                ("target_role", "VARCHAR(255)"),
            ],
            "interview_sessions": [
                ("target_roles", "JSON"),
                ("custom_role_description", "TEXT"),
                ("assessment_plan", "JSON"),
                ("competency_state", "JSON"),
                ("completion_reason", "VARCHAR(100)"),
                ("evidence_coverage_ratio", "FLOAT DEFAULT 0.0"),
            ],
            "questions": [
                ("target_competency", "VARCHAR(255)"),
                ("assessment_objective", "TEXT"),
                ("is_followup", "BOOLEAN DEFAULT 0"),
                ("question_plan", "JSON"),
                ("coach_lead_in", "TEXT"),
            ],
            "session_reports": [
                ("role_competency_profile", "JSON"),
            ],
            "experiment_sessions": [
                ("execution_provenance", "VARCHAR(50) DEFAULT 'SYNTHETIC'"),
            ],
            "experiment_trials": [
                ("evaluator_provider", "VARCHAR(100) DEFAULT 'GROUNDED_NLP'"),
                ("evaluator_version", "VARCHAR(50) DEFAULT 'v1.0'"),
                ("rubric_version", "VARCHAR(50) DEFAULT 'technical_v1'"),
                ("evaluator_fallback", "BOOLEAN DEFAULT 0"),
                ("fallback_reason", "VARCHAR(255)"),
                ("form_id", "VARCHAR(20) DEFAULT 'FORM_A'"),
                ("execution_provenance", "VARCHAR(50) DEFAULT 'SYNTHETIC'"),
            ],
            "roadmap_items": [
                ("topics_to_study", "JSON"),
                ("practical_exercises", "JSON"),
                ("implementation_task", "JSON"),
                ("expected_deliverables", "JSON"),
                ("estimated_duration", "VARCHAR(100) DEFAULT '1-2 weeks'"),
                ("difficulty_level", "VARCHAR(50) DEFAULT 'INTERMEDIATE'"),
                ("evaluation_criteria", "JSON"),
                ("evidence_required", "TEXT"),
                ("prerequisite_milestone_ids", "JSON"),
                ("mapping_status", "VARCHAR(50) DEFAULT 'MAPPED'"),
                ("is_flagged_for_review", "BOOLEAN DEFAULT 0"),
                ("progression_tier", "VARCHAR(100) DEFAULT 'Tier 1: Assessed, Needs Practice'"),
                ("proficiency_state", "VARCHAR(50) DEFAULT 'NOT_ASSESSED'"),
            ],
        }
        for table, cols in table_columns.items():
            res = await conn.execute(text(f"PRAGMA table_info({table})"))
            existing = [row[1] for row in res.fetchall()]
            if existing:
                for col_name, col_type in cols:
                    if col_name not in existing:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
    except Exception as e:
        logger.debug(f"SQLite migration check notice: {e}")


async def _migrate_postgres_columns(conn):
    """Ensures newly added columns are present in existing PostgreSQL tables."""
    try:
        table_columns = {
            "candidates": [
                ("password_hash", "VARCHAR(255)"),
            ],
            "interview_sessions": [
                ("target_roles", "JSONB"),
                ("custom_role_description", "TEXT"),
                ("assessment_plan", "JSONB"),
                ("competency_state", "JSONB"),
            ],
            "questions": [
                ("target_competency", "VARCHAR(255)"),
                ("assessment_objective", "TEXT"),
                ("is_followup", "BOOLEAN DEFAULT FALSE"),
                ("question_plan", "JSONB"),
                ("coach_lead_in", "TEXT"),
            ],
            "session_reports": [
                ("role_competency_profile", "JSONB"),
            ],
            "experiment_sessions": [
                ("execution_provenance", "VARCHAR(50) DEFAULT 'SYNTHETIC'"),
            ],
            "experiment_trials": [
                ("evaluator_provider", "VARCHAR(100) DEFAULT 'GROUNDED_NLP'"),
                ("evaluator_version", "VARCHAR(50) DEFAULT 'v1.0'"),
                ("rubric_version", "VARCHAR(50) DEFAULT 'technical_v1'"),
                ("evaluator_fallback", "BOOLEAN DEFAULT FALSE"),
                ("fallback_reason", "VARCHAR(255)"),
                ("form_id", "VARCHAR(20) DEFAULT 'FORM_A'"),
                ("execution_provenance", "VARCHAR(50) DEFAULT 'SYNTHETIC'"),
            ],
            "roadmap_items": [
                ("topics_to_study", "JSONB"),
                ("practical_exercises", "JSONB"),
                ("implementation_task", "JSONB"),
                ("expected_deliverables", "JSONB"),
                ("estimated_duration", "VARCHAR(100) DEFAULT '1-2 weeks'"),
                ("difficulty_level", "VARCHAR(50) DEFAULT 'INTERMEDIATE'"),
                ("evaluation_criteria", "JSONB"),
                ("evidence_required", "TEXT"),
                ("prerequisite_milestone_ids", "JSONB"),
                ("mapping_status", "VARCHAR(50) DEFAULT 'MAPPED'"),
                ("is_flagged_for_review", "BOOLEAN DEFAULT FALSE"),
                ("progression_tier", "VARCHAR(100) DEFAULT 'Tier 1: Assessed, Needs Practice'"),
                ("proficiency_state", "VARCHAR(50) DEFAULT 'NOT_ASSESSED'"),
            ],
        }
        for table, cols in table_columns.items():
            for col_name, col_type in cols:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
    except Exception as e:
        logger.debug(f"PostgreSQL migration check notice: {e}")


async def _init_engine():
    """
    Create the engine, test PostgreSQL, and fall back to single-pool SQLite if unreachable.
    """
    global _engine, _AsyncSessionLocal, _engine_initialized
    if _engine_initialized:
        return _engine

    db_url = settings.get_database_url()
    is_postgres = "postgresql" in db_url

    if is_postgres:
        try:
            candidate = create_async_engine(db_url, echo=False, future=True, pool_pre_ping=True)
            async with candidate.connect() as conn:
                await conn.execute(text("SELECT 1"))
            _engine = candidate
            logger.info("Connected to PostgreSQL successfully.")
        except Exception as e:
            logger.warning(f"PostgreSQL not reachable ({e}), falling back to persistent local SQLite.")
            _engine = create_async_engine(
                SQLITE_FALLBACK_URL,
                echo=False,
                future=True,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False, "timeout": 30},
            )
    else:
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            poolclass=StaticPool if "sqlite" in db_url else None,
            connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in db_url else {},
        )

    # Ensure tables are created on the active engine
    from backend.models.base import Base
    import backend.models.candidate  # noqa
    import backend.models.resume     # noqa
    import backend.models.embedding  # noqa
    import backend.models.interview  # noqa
    import backend.models.resume_claim  # noqa
    import backend.models.skill_state  # noqa
    import backend.models.transfer_task  # noqa
    import backend.models.transfer_diagnosis  # noqa
    import backend.models.coaching_event  # noqa
    import backend.models.experiment  # noqa
    import backend.models.roadmap  # noqa
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in str(_engine.url):
            await _migrate_sqlite_columns(conn)
        else:
            await _migrate_postgres_columns(conn)

    _AsyncSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    _engine_initialized = True
    return _engine


def reset_engine():
    """Resets the module-level cached engine and sessionmaker (used for test isolation)."""
    global _engine, _AsyncSessionLocal, _engine_initialized
    _engine = None
    _AsyncSessionLocal = None
    _engine_initialized = False


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    db_url = settings.get_database_url()
    _engine = create_async_engine(
        db_url if db_url else SQLITE_FALLBACK_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    return _engine


def get_sessionmaker():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = get_engine()
        _AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency providing an async database session per request.
    """
    global _AsyncSessionLocal

    if not _engine_initialized:
        await _init_engine()

    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
