"""toddlers_metadata

Revision ID: fcbc311ee086
Revises: fa63edde8c99
Create Date: 2025-07-19 09:28:22.547684

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fcbc311ee086"
down_revision: Union[str, None] = "fa63edde8c99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO education_levels (id, level_name) 
        VALUES (3, 'Pre-School Development')
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO curriculum_areas (id, area_name)
        VALUES (7, 'Early Development')
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO school_years (id, level_id, year_name, year_order) VALUES
        (9, 3, 'Age 2-3', -2),  -- to compensate for all other school years, which start at 1
        (10, 3, 'Age 3-4', -1),
        (11, 3, 'Age 4-5', 0)
        ON CONFLICT (id) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO subjects (id, area_id, subject_name, introduction_year_id, is_core) VALUES
        (20, 7, 'Communication & Language', 9, true),
        (21, 7, 'Social & Emotional', 9, true),
        (22, 7, 'Physical Development', 9, true), 
        (23, 7, 'Cognitive Skills', 9, true),
        (24, 7, 'Independence & Self-Care', 9, true)
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM subjects WHERE id IN (20, 21, 22, 23, 24)
        """
    )

    op.execute(
        """
        DELETE FROM school_years WHERE id IN (9, 10, 11)
        """
    )

    op.execute(
        """
        DELETE FROM curriculum_areas WHERE id IN (7)
        """
    )

    op.execute(
        """
        DELETE FROM education_levels WHERE id IN (3)
        """
    )
