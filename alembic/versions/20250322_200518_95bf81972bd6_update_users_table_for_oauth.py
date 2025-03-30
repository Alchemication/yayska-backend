"""update_users_table_for_oauth

Revision ID: 95bf81972bd6
Revises: b90f7dfa16c2
Create Date: 2025-03-22 20:05:18.118734

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95bf81972bd6"
down_revision: Union[str, None] = "b90f7dfa16c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add google_id column
    op.execute("""
        ALTER TABLE users
        ADD COLUMN google_id VARCHAR(255) UNIQUE
    """)

    # Add picture_url column
    op.execute("""
        ALTER TABLE users
        ADD COLUMN picture_url VARCHAR(512)
    """)

    # Modify hashed_password to be nullable for OAuth users
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN hashed_password DROP NOT NULL
    """)

    # Create index on google_id
    op.execute("""
        CREATE INDEX ix_users_google_id ON users (google_id)
    """)


def downgrade() -> None:
    # Drop index
    op.execute("DROP INDEX IF EXISTS ix_users_google_id")

    # Make hashed_password NOT NULL again
    op.execute("""
        UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL;
        ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL
    """)

    # Drop columns
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS google_id,
        DROP COLUMN IF EXISTS picture_url
    """)
