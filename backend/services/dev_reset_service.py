"""
Development Database Reset Service.
Provides a strictly guarded, transaction-safe procedure to reset development/test
candidate records, evaluations, coaching history, vector chunks, and conversations
while preserving schemas, migrations, configuration, and reference curriculum data.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Tables storing candidate-related data in strict reverse dependency order (leaves to root)
CANDIDATE_DATA_TABLES: List[str] = [
    "coaching_intervention_events",
    "transfer_diagnoses",
    "transfer_attempts",
    "roadmap_items",
    "personalized_roadmaps",
    "conversation_messages",
    "conversations",
    "session_reports",
    "evaluations",
    "answers",
    "questions",
    "interview_sessions",
    "candidate_skill_states",
    "candidate_claims",
    "resume_chunks",  # Vector embeddings store
    "candidate_profiles",
    "resumes",
    "experiment_retention_schedules",
    "experiment_consents",
    "experiment_participant_assignments",
    "experiment_trials",
    "experiment_sessions",
    "candidates",
]

# System / Reference tables that MUST BE PRESERVED during reset
PRESERVED_SYSTEM_TABLES: List[str] = [
    "transfer_tasks",  # Core transfer curriculum and task library (L0-L5 scenarios)
]

CONFIRMATION_PHRASE = "CONFIRM_DEVELOPMENT_RESET"


def is_production_environment() -> bool:
    """Checks whether the application is running in production."""
    env = (os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "development")).strip().lower()
    return env == "production"


def is_verified_development_database(db_url: str) -> bool:
    """
    Validates that the target database URL points to a legitimate local development or test database.
    Rejects production connection strings, cloud endpoints, and unverified hosts.
    """
    if not db_url or not isinstance(db_url, str):
        return False

    url_lower = db_url.lower()

    # Disallow production substrings
    if any(keyword in url_lower for keyword in ["prod", "production", "live"]):
        return False

    # Disallow cloud-hosted production database domains
    cloud_prod_hosts = [
        "amazonaws.com",
        "rds.",
        "cloudsql",
        "azure.com",
        "supabase.co",
        "neon.tech",
        "cockroachlabs.cloud",
    ]
    if any(host in url_lower for host in cloud_prod_hosts):
        return False

    # Allow local SQLite databases
    if "sqlite" in url_lower:
        # Must be local file or in-memory
        return True

    # Allow local PostgreSQL development databases
    if "postgresql" in url_lower or "postgres" in url_lower:
        allowed_local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"]
        has_local_host = any(host in url_lower for host in allowed_local_hosts)
        # Verify db name is dev/test/ai_interview_coach
        allowed_db_names = ["ai_interview_coach", "dev", "test", "postgres"]
        has_allowed_db = any(db in url_lower for db in allowed_db_names)
        return has_local_host and has_allowed_db

    return False


class DevelopmentDatabaseResetService:
    """
    Guarded service to execute development database resets.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def execute_reset(
        self,
        confirmation: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Executes a transactional reset of all development candidate data.

        Safety preconditions:
        1. Explicit confirmation string must match 'CONFIRM_DEVELOPMENT_RESET'.
        2. ENVIRONMENT must NOT be 'production'.
        3. Database URL must be verified as a local development/test database.
        """
        effective_session = db_session or self.session
        if not effective_session:
            raise ValueError("An active database session is required to execute database reset.")

        # 1. Check confirmation
        if str(confirmation).strip() != CONFIRMATION_PHRASE:
            raise ValueError(
                f"Confirmation rejected. You must provide exact phrase '{CONFIRMATION_PHRASE}' to execute database reset."
            )

        # 2. Check production environment
        if is_production_environment():
            raise RuntimeError(
                "Execution Refused: Database reset is strictly disabled in production environment."
            )

        # 3. Check database URL
        db_url = settings.get_database_url()
        if not is_verified_development_database(db_url):
            raise RuntimeError(
                f"Execution Refused: Database URL '{db_url}' is not a verified development or test database."
            )

        cleared_counts: Dict[str, int] = {}
        total_cleared = 0

        # Run inside transaction block
        try:
            # Check existing tables in DB to avoid errors on tables not yet created
            is_sqlite = "sqlite" in str(effective_session.bind.url if effective_session.bind else db_url).lower()

            if is_sqlite:
                tables_res = await effective_session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                existing_tables = set(r[0] for r in tables_res.fetchall())
            else:
                tables_res = await effective_session.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                )
                existing_tables = set(r[0] for r in tables_res.fetchall())

            # Delete rows in reverse foreign key order
            for table_name in CANDIDATE_DATA_TABLES:
                if table_name not in existing_tables:
                    continue

                # Count rows before deletion
                count_res = await effective_session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                row_count = count_res.scalar() or 0

                if row_count > 0:
                    await effective_session.execute(text(f'DELETE FROM "{table_name}"'))
                    cleared_counts[table_name] = row_count
                    total_cleared += row_count
                else:
                    cleared_counts[table_name] = 0

            # Commit the deletions
            await effective_session.commit()

            # Verify preserved reference data
            preserved_task_count = 0
            if "transfer_tasks" in existing_tables:
                task_res = await effective_session.execute(text('SELECT COUNT(*) FROM "transfer_tasks"'))
                preserved_task_count = task_res.scalar() or 0

            return {
                "status": "success",
                "message": "Development database reset completed successfully.",
                "database_target": "SQLite Local" if is_sqlite else "PostgreSQL Local Dev",
                "cleared_records": cleared_counts,
                "total_records_cleared": total_cleared,
                "preserved_system_tables": {
                    "transfer_tasks": preserved_task_count,
                },
            }

        except Exception as e:
            await effective_session.rollback()
            logger.error(f"Development database reset failed: {e}", exc_info=True)
            raise RuntimeError(f"Database reset failed and was rolled back: {str(e)}") from e
