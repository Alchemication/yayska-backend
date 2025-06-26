"""ai_chat_feeback_cols

Revision ID: e635c333e57e
Revises: efd0655774c6
Create Date: 2025-06-21 21:39:07.314182

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e635c333e57e"
down_revision: Union[str, None] = "efd0655774c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add feedback_thumbs (int) and feedback_text (text, max length 2056) columns to chat_messages
    op.execute("""
        ALTER TABLE chat_messages
        ADD COLUMN feedback_thumbs INTEGER,
        ADD COLUMN feedback_text VARCHAR(2056)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE chat_messages
        DROP COLUMN IF EXISTS feedback_thumbs,
        DROP COLUMN IF EXISTS feedback_text
    """)
