"""daily limit in LLM calls

Revision ID: 75ab931da967
Revises: 8843bced378c
Create Date: 2025-06-26 21:54:07.644387

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75ab931da967"
down_revision: Union[str, None] = "8843bced378c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN ai_chat_request_daily_count INTEGER NOT NULL DEFAULT 0;
    """
    )
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN last_ai_chat_request_date DATE;
    """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        DROP COLUMN IF EXISTS ai_chat_request_daily_count;
    """
    )
    op.execute(
        """
        ALTER TABLE users
        DROP COLUMN IF EXISTS last_ai_chat_request_date;
    """
    )
