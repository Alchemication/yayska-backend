"""improved_events

Revision ID: efd0655774c6
Revises: 094e4d72dbb1
Create Date: 2025-06-15 13:55:37.395694

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "efd0655774c6"
down_revision: Union[str, None] = "094e4d72dbb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to the events table
    op.execute("ALTER TABLE events ADD COLUMN session_id VARCHAR(255)")
    op.execute("ALTER TABLE events ADD COLUMN ip_address INET")
    op.execute("ALTER TABLE events ADD COLUMN user_agent TEXT")
    op.execute("ALTER TABLE events ADD COLUMN source VARCHAR(50) DEFAULT 'web'")

    # Add indexes for better query performance
    op.execute("CREATE INDEX idx_events_user_id ON events(user_id)")
    op.execute("CREATE INDEX idx_events_event_type ON events(event_type)")
    op.execute("CREATE INDEX idx_events_created_at ON events(created_at)")
    op.execute("CREATE INDEX idx_events_session_id ON events(session_id)")


def downgrade() -> None:
    # Remove indexes
    op.execute("DROP INDEX IF EXISTS idx_events_session_id")
    op.execute("DROP INDEX IF EXISTS idx_events_created_at")
    op.execute("DROP INDEX IF EXISTS idx_events_event_type")
    op.execute("DROP INDEX IF EXISTS idx_events_user_id")

    # Remove columns
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS source")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS user_agent")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS ip_address")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS session_id")
