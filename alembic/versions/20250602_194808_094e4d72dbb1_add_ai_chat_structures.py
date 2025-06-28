"""add_ai_chat_structures

Revision ID: 094e4d72dbb1
Revises: 61644c38a317
Create Date: 2025-06-02 19:48:08.047095

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "094e4d72dbb1"
down_revision: Union[str, None] = "61644c38a317"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add memory column to users table
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN memory JSONB DEFAULT '{}'::jsonb
    """)

    # Create children table
    op.execute("""
        CREATE TABLE children (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            school_year_id INTEGER REFERENCES school_years(id),  -- Links to existing curriculum structure
            memory JSONB DEFAULT '{}'::jsonb,  -- child-specific learning patterns
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    """)

    # Create chat sessions table
    op.execute("""
        CREATE TABLE chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,  -- nullable for general sessions
            title VARCHAR(200),
            entry_point_type VARCHAR(50) NOT NULL,
            entry_point_context JSONB DEFAULT '{}'::jsonb,  -- {month_id: 1, concept_id: 123, etc.}
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
        )
    """)

    # Create messages table
    op.execute("""
        CREATE TABLE chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,  -- 'user', 'assistant'
            reasoning TEXT,
            content TEXT NOT NULL,
            context_snapshot JSONB DEFAULT '{}'::jsonb,  -- context snapshots, etc.
            llm_usage JSONB DEFAULT '{}'::jsonb,  -- token usage data
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for efficient querying
    index_statements = [
        "CREATE INDEX idx_children_user_id ON children(user_id)",
        "CREATE INDEX idx_children_school_year_id ON children(school_year_id)",
        "CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id)",
        "CREATE INDEX idx_chat_sessions_child_id ON chat_sessions(child_id)",
        "CREATE INDEX idx_chat_sessions_entry_point_type ON chat_sessions(entry_point_type)",
        "CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC)",
        "CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id)",
        "CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at)",
        "CREATE INDEX idx_chat_messages_role ON chat_messages(role)",
    ]

    for statement in index_statements:
        op.execute(statement)


def downgrade() -> None:
    # Drop in reverse order
    statements = [
        "DROP INDEX IF EXISTS idx_chat_messages_role",
        "DROP INDEX IF EXISTS idx_chat_messages_created_at",
        "DROP INDEX IF EXISTS idx_chat_messages_session_id",
        "DROP INDEX IF EXISTS idx_chat_sessions_updated_at",
        "DROP INDEX IF EXISTS idx_chat_sessions_entry_point_type",
        "DROP INDEX IF EXISTS idx_chat_sessions_user_id",
        "DROP INDEX IF EXISTS idx_chat_sessions_child_id",
        "DROP INDEX IF EXISTS idx_children_school_year_id",
        "DROP INDEX IF EXISTS idx_children_user_id",
        "DROP TABLE IF EXISTS chat_messages",
        "DROP TABLE IF EXISTS chat_sessions",
        "DROP TABLE IF EXISTS children",
    ]

    for statement in statements:
        op.execute(statement)

    # Remove memory column from users
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS memory")
