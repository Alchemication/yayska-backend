"""add_monthly_curriculum_plans_table

Revision ID: b90f7dfa16c2
Revises: 632beec733a9
Create Date: 2025-03-09 13:06:34.686215

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b90f7dfa16c2"
down_revision: Union[str, None] = "632beec733a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the monthly_curriculum_plans table
    op.execute("""
        CREATE TABLE monthly_curriculum_plans (
            year_id INTEGER NOT NULL REFERENCES school_years(id),
            month_order INTEGER NOT NULL,
            month_name VARCHAR(20) NOT NULL,
            essential_concept_ids INTEGER[] NOT NULL,
            important_concept_ids INTEGER[] NOT NULL,
            supplementary_concept_ids INTEGER[] NOT NULL,
            focus_statement TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (year_id, month_order)
        )
    """)

    # Create the index for faster array operations
    op.execute("""
        CREATE INDEX idx_monthly_curriculum_plans_essential_concept_ids 
        ON monthly_curriculum_plans USING GIN(essential_concept_ids)
    """)
    op.execute("""
        CREATE INDEX idx_monthly_curriculum_plans_important_concept_ids 
        ON monthly_curriculum_plans USING GIN(important_concept_ids)
    """)
    op.execute("""
        CREATE INDEX idx_monthly_curriculum_plans_supplementary_concept_ids 
        ON monthly_curriculum_plans USING GIN(supplementary_concept_ids)
    """)


def downgrade() -> None:
    # Drop index and table
    op.execute(
        "DROP INDEX IF EXISTS idx_monthly_curriculum_plans_essential_concept_ids"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_monthly_curriculum_plans_important_concept_ids"
    )
    op.execute(
        "DROP INDEX IF EXISTS idx_monthly_curriculum_plans_supplementary_concept_ids"
    )
    op.execute("DROP TABLE IF EXISTS monthly_curriculum_plans")
