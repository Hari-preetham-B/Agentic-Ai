"""Row Level Security (RLS) for user-owned tables.

Enables RLS on user-owned tables and creates policies that restrict
access to rows belonging to the authenticated user.

Revision ID: 0006_row_level_security
Revises: 0005_adaptive_interview
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_row_level_security"
down_revision: Union[str, None] = "0005_adaptive_interview"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql() -> bool:
    """Check if we're running against PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        # RLS is PostgreSQL-specific. Skip on SQLite (tests).
        return

    # Enable RLS on user-owned tables.
    tables = [
        "profiles",
        "education",
        "skills",
        "projects",
        "experience",
        "career_goals",
        "agent_runs",
        "agent_events",
        "roadmaps",
        "roadmap_items",
        "roadmap_resources",
        "interview_sessions",
        "interview_turns",
        "interview_skill_results",
        "claims",
    ]

    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Create policies for profiles (direct user ownership via user_id).
    op.execute("""
        CREATE POLICY profiles_select_own ON profiles
        FOR SELECT USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY profiles_insert_own ON profiles
        FOR INSERT WITH CHECK (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY profiles_update_own ON profiles
        FOR UPDATE USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY profiles_delete_own ON profiles
        FOR DELETE USING (auth.uid() = user_id)
    """)

    # Create policies for child tables (ownership via profile_id → profiles.user_id).
    child_tables = [
        "education", "skills", "projects", "experience", "career_goals",
    ]
    for table in child_tables:
        op.execute(f"""
            CREATE POLICY {table}_select_own ON {table}
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = {table}.profile_id
                    AND profiles.user_id = auth.uid()
                )
            )
        """)
        op.execute(f"""
            CREATE POLICY {table}_insert_own ON {table}
            FOR INSERT WITH CHECK (
                EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = {table}.profile_id
                    AND profiles.user_id = auth.uid()
                )
            )
        """)
        op.execute(f"""
            CREATE POLICY {table}_update_own ON {table}
            FOR UPDATE USING (
                EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = {table}.profile_id
                    AND profiles.user_id = auth.uid()
                )
            )
        """)
        op.execute(f"""
            CREATE POLICY {table}_delete_own ON {table}
            FOR DELETE USING (
                EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = {table}.profile_id
                    AND profiles.user_id = auth.uid()
                )
            )
        """)

    # Agent runs: ownership via profile_id.
    op.execute("""
        CREATE POLICY agent_runs_select_own ON agent_runs
        FOR SELECT USING (
            profile_id IS NULL OR EXISTS (
                SELECT 1 FROM profiles
                WHERE profiles.id = agent_runs.profile_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)

    # Agent events: ownership via agent_run_id → agent_runs.
    op.execute("""
        CREATE POLICY agent_events_select_own ON agent_events
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM agent_runs
                WHERE agent_runs.id = agent_events.agent_run_id
                AND (agent_runs.profile_id IS NULL OR EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = agent_runs.profile_id
                    AND profiles.user_id = auth.uid()
                ))
            )
        )
    """)

    # Roadmaps: ownership via profile_id.
    for table in ["roadmaps", "roadmap_items", "roadmap_resources"]:
        if table == "roadmaps":
            op.execute(f"""
                CREATE POLICY {table}_select_own ON {table}
                FOR SELECT USING (
                    EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = {table}.profile_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_insert_own ON {table}
                FOR INSERT WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = {table}.profile_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_update_own ON {table}
                FOR UPDATE USING (
                    EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = {table}.profile_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_delete_own ON {table}
                FOR DELETE USING (
                    EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = {table}.profile_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
        elif table == "roadmap_items":
            op.execute(f"""
                CREATE POLICY {table}_select_own ON {table}
                FOR SELECT USING (
                    EXISTS (
                        SELECT 1 FROM roadmaps
                        JOIN profiles ON profiles.id = roadmaps.profile_id
                        WHERE roadmaps.id = {table}.roadmap_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_insert_own ON {table}
                FOR INSERT WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM roadmaps
                        JOIN profiles ON profiles.id = roadmaps.profile_id
                        WHERE roadmaps.id = {table}.roadmap_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_update_own ON {table}
                FOR UPDATE USING (
                    EXISTS (
                        SELECT 1 FROM roadmaps
                        JOIN profiles ON profiles.id = roadmaps.profile_id
                        WHERE roadmaps.id = {table}.roadmap_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_delete_own ON {table}
                FOR DELETE USING (
                    EXISTS (
                        SELECT 1 FROM roadmaps
                        JOIN profiles ON profiles.id = roadmaps.profile_id
                        WHERE roadmaps.id = {table}.roadmap_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)
        elif table == "roadmap_resources":
            op.execute(f"""
                CREATE POLICY {table}_select_own ON {table}
                FOR SELECT USING (
                    EXISTS (
                        SELECT 1 FROM roadmap_items
                        JOIN roadmaps ON roadmaps.id = roadmap_items.roadmap_id
                        JOIN profiles ON profiles.id = roadmaps.profile_id
                        WHERE roadmap_items.id = {table}.roadmap_item_id
                        AND profiles.user_id = auth.uid()
                    )
                )
            """)

    # Interview sessions: ownership via profile_id.
    op.execute("""
        CREATE POLICY interview_sessions_select_own ON interview_sessions
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM profiles
                WHERE profiles.id = interview_sessions.profile_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY interview_sessions_insert_own ON interview_sessions
        FOR INSERT WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles
                WHERE profiles.id = interview_sessions.profile_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)

    # Interview turns: ownership via session_id → interview_sessions.
    op.execute("""
        CREATE POLICY interview_turns_select_own ON interview_turns
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM interview_sessions
                JOIN profiles ON profiles.id = interview_sessions.profile_id
                WHERE interview_sessions.id = interview_turns.session_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)

    # Interview skill results: ownership via session_id.
    op.execute("""
        CREATE POLICY interview_skill_results_select_own ON interview_skill_results
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM interview_sessions
                JOIN profiles ON profiles.id = interview_sessions.profile_id
                WHERE interview_sessions.id = interview_skill_results.session_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)

    # Claims: ownership via profile_id.
    op.execute("""
        CREATE POLICY claims_select_own ON claims
        FOR SELECT USING (
            profile_id IS NULL OR EXISTS (
                SELECT 1 FROM profiles
                WHERE profiles.id = claims.profile_id
                AND profiles.user_id = auth.uid()
            )
        )
    """)


def downgrade() -> None:
    if not _is_postgresql():
        return

    tables = [
        "profiles", "education", "skills", "projects", "experience",
        "career_goals", "agent_runs", "agent_events", "roadmaps",
        "roadmap_items", "roadmap_resources", "interview_sessions",
        "interview_turns", "interview_skill_results", "claims",
    ]
    for table in tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
