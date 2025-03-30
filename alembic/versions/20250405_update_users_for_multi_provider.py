"""update_users_for_multi_provider

Revision ID: 20250405_01
Revises: 95bf81972bd6
Create Date: 2025-04-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250405_01"
down_revision: Union[str, None] = "95bf81972bd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename google_id to provider_user_id and add provider column
    op.execute("""
        ALTER TABLE users
        ADD COLUMN provider VARCHAR(50),
        ADD COLUMN provider_user_id VARCHAR(255),
        ADD COLUMN provider_data JSONB,
        ADD COLUMN platform VARCHAR(20)
    """)

    # Migrate existing google_id data
    op.execute("""
        UPDATE users 
        SET provider = 'google', 
            provider_user_id = google_id,
            platform = 'web'
        WHERE google_id IS NOT NULL
    """)

    # Create new composite index
    op.execute("""
        CREATE UNIQUE INDEX ix_users_provider_userid
        ON users (provider, provider_user_id)
        WHERE provider IS NOT NULL AND provider_user_id IS NOT NULL
    """)

    # Don't drop the google_id column immediately for safety
    # We'll do that in a future migration after verifying all data is migrated


def downgrade() -> None:
    # Drop provider columns and index
    op.execute("DROP INDEX IF EXISTS ix_users_provider_userid")
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS provider,
        DROP COLUMN IF EXISTS provider_user_id,
        DROP COLUMN IF EXISTS provider_data,
        DROP COLUMN IF EXISTS platform
    """)
