"""user_interactions

Revision ID: fa63edde8c99
Revises: 75ab931da967
Create Date: 2025-07-03 08:19:55.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa63edde8c99"
down_revision: Union[str, None] = "75ab931da967"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_interactions (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(255),
            interaction_type VARCHAR(50) NOT NULL,
            interaction_context JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    op.execute(
        "CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);"
    )
    op.execute(
        "CREATE INDEX idx_user_interactions_session_id ON user_interactions(session_id);"
    )
    op.execute(
        "CREATE INDEX idx_user_interactions_interaction_type ON user_interactions(interaction_type);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_interactions;")
