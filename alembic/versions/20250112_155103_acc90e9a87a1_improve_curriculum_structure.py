"""improve curriculum structure

Revision ID: acc90e9a87a1
Revises: 84e48761155c
Create Date: 2025-01-12 15:51:03.605513

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "acc90e9a87a1"
down_revision: Union[str, None] = "84e48761155c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    statements = [
        """ALTER TABLE subjects 
           ADD COLUMN introduction_year_id INTEGER 
           REFERENCES school_years(id)""",
        """ALTER TABLE subjects 
           ADD COLUMN is_core BOOLEAN 
           DEFAULT false""",
        """ALTER TABLE learning_outcomes 
           ADD COLUMN success_criteria text[]""",
    ]

    # Execute statements individually
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    statements = [
        # Remove learning_outcomes columns
        """ALTER TABLE learning_outcomes 
           DROP COLUMN IF EXISTS success_criteria""",
        """ALTER TABLE learning_outcomes 
           DROP COLUMN IF EXISTS learning_objective""",
        # Remove subjects columns
        """ALTER TABLE subjects 
           DROP COLUMN IF EXISTS is_core""",
        """ALTER TABLE subjects 
           DROP COLUMN IF EXISTS introduction_year_id""",
    ]

    # Execute statements individually
    for statement in statements:
        op.execute(statement)
