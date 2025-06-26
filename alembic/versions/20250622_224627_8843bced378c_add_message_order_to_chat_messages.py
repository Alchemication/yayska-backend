"""add_message_order_to_chat_messages

Revision ID: 8843bced378c
Revises: e635c333e57e
Create Date: 2025-06-22 22:46:27.420235

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8843bced378c"
down_revision: Union[str, None] = "e635c333e57e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add an auto-incrementing integer column to guarantee message order
    op.execute("""
        ALTER TABLE chat_messages
        ADD COLUMN message_order SERIAL;
    """)
    # Add an index for performance when ordering by this new column
    op.execute("""
        CREATE INDEX idx_chat_messages_message_order ON chat_messages(message_order);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_chat_messages_message_order;
    """)
    op.execute("""
        ALTER TABLE chat_messages
        DROP COLUMN IF EXISTS message_order;
    """)
