"""add_token_blacklist_table

Revision ID: 61644c38a317
Revises: 20250405_01
Create Date: 2025-03-23 19:54:33.140735

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61644c38a317"
down_revision: Union[str, None] = "20250405_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create token blacklist table using raw SQL
    op.execute("""
        CREATE TABLE token_blacklist (
            id SERIAL PRIMARY KEY,
            token VARCHAR(500) NOT NULL UNIQUE,
            user_id INTEGER,
            token_type VARCHAR(20) NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            blacklisted_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """)

    # Create indexes separately
    op.execute("""
        CREATE INDEX ix_token_blacklist_token ON token_blacklist (token)
    """)

    op.execute("""
        CREATE INDEX ix_token_blacklist_user_id ON token_blacklist (user_id)
    """)

    op.execute("""
        CREATE INDEX ix_token_blacklist_expires_at ON token_blacklist (expires_at)
    """)


def downgrade() -> None:
    # Drop token blacklist table using raw SQL
    op.execute("""
        DROP TABLE IF EXISTS token_blacklist CASCADE
    """)
