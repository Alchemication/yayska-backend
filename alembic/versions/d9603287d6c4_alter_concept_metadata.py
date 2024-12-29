"""alter concept metadata

Revision ID: d9603287d6c4
Revises: 973d815d64dd
Create Date: 2024-12-29 09:55:03.936816

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9603287d6c4"
down_revision: Union[str, None] = "973d815d64dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing columns
    op.execute("ALTER TABLE concept_metadata DROP COLUMN real_world_application")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN common_misconceptions")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN teaching_tips")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN parent_guidance")

    # Add new JSONB columns
    op.execute("ALTER TABLE concept_metadata ADD COLUMN why_important JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN difficulty_stats JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN parent_guide JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN real_world JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN learning_path JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN time_guide JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN assessment_approaches JSONB")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN irish_language_support JSONB")

    # Create GIN indexes for JSONB columns that will be frequently queried
    op.execute(
        "CREATE INDEX idx_concept_metadata_why_important ON concept_metadata USING GIN (why_important)"
    )
    op.execute(
        "CREATE INDEX idx_concept_metadata_learning_path ON concept_metadata USING GIN (learning_path)"
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_concept_metadata_why_important")
    op.execute("DROP INDEX IF EXISTS idx_concept_metadata_learning_path")

    # Drop new columns
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS why_important")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS difficulty_stats")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS parent_guide")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS real_world")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS learning_path")
    op.execute("ALTER TABLE concept_metadata DROP COLUMN IF EXISTS time_guide")
    op.execute(
        "ALTER TABLE concept_metadata DROP COLUMN IF EXISTS assessment_approaches"
    )
    op.execute(
        "ALTER TABLE concept_metadata DROP COLUMN IF EXISTS irish_language_support"
    )

    # Add back original columns
    op.execute("ALTER TABLE concept_metadata ADD COLUMN real_world_application TEXT")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN common_misconceptions TEXT")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN teaching_tips TEXT")
    op.execute("ALTER TABLE concept_metadata ADD COLUMN parent_guidance TEXT")
