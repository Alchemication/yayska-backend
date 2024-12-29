"""add events

Revision ID: 973d815d64dd
Revises: 05552223099a
Create Date: 2024-12-28 23:08:31.592164

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "973d815d64dd"
down_revision: Union[str, None] = "05552223099a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    statement = """
        CREATE TABLE events (
            id BIGSERIAL PRIMARY KEY,  -- Use BIGSERIAL instead of SERIAL for larger range
            created_at TIMESTAMP NOT NULL,
            user_id INTEGER NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            payload JSONB
        )
    """
    op.execute(statement)


def downgrade() -> None:
    statement = "DROP TABLE IF EXISTS events"
    op.execute(statement)
