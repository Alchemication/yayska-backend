"""init_db

Revision ID: 05552223099a
Revises:
Create Date: 2024-12-24 22:39:29.294358

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05552223099a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define SQL statements as individual commands
    statements = [
        """CREATE TABLE education_levels (
            id SERIAL PRIMARY KEY,
            level_name VARCHAR(50)  -- Primary, Secondary
        )""",
        """CREATE TABLE curriculum_areas (
            id SERIAL PRIMARY KEY,
            area_name VARCHAR(100)  -- Language, Mathematics, SESE, Arts, etc.
        )""",
        """CREATE TABLE subjects (
            id SERIAL PRIMARY KEY,
            area_id INT,
            subject_name VARCHAR(100),  -- Mathematics, English, Irish, etc.
            FOREIGN KEY (area_id) REFERENCES curriculum_areas(id)
        )""",
        """CREATE TABLE strands (
            id SERIAL PRIMARY KEY,
            subject_id INT,
            strand_name VARCHAR(200),  -- Numbers, Algebra, etc.
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )""",
        """CREATE TABLE strand_units (
            id SERIAL PRIMARY KEY,
            strand_id INT,
            unit_name VARCHAR(200),  -- Counting and numeration, etc.
            FOREIGN KEY (strand_id) REFERENCES strands(id)
        )""",
        """CREATE TABLE school_years (
            id SERIAL PRIMARY KEY,
            level_id INT,
            year_name VARCHAR(50),  -- Junior Infants, Senior Infants, First Class, etc.
            year_order INT,         -- For proper sorting
            FOREIGN KEY (level_id) REFERENCES education_levels(id)
        )""",
        """CREATE TABLE learning_outcomes (
            id SERIAL PRIMARY KEY,
            unit_id INT,
            year_id INT,
            outcome_description TEXT,
            prerequisite_knowledge TEXT,
            complexity_level INT,
            FOREIGN KEY (unit_id) REFERENCES strand_units(id),
            FOREIGN KEY (year_id) REFERENCES school_years(id)
        )""",
        """CREATE TABLE concepts (
            id SERIAL PRIMARY KEY,
            outcome_id INT,
            concept_name VARCHAR(200),
            concept_description TEXT,
            difficulty_level INT,
            FOREIGN KEY (outcome_id) REFERENCES learning_outcomes(id)
        )""",
        """CREATE TABLE quizzes (
            id SERIAL PRIMARY KEY,
            concept_id INT,
            quiz_type VARCHAR(50),
            difficulty_level INT,
            FOREIGN KEY (concept_id) REFERENCES concepts(id)
        )""",
        """CREATE TABLE concept_metadata (
            id SERIAL PRIMARY KEY,
            concept_id INT,
            real_world_application TEXT,
            common_misconceptions TEXT,
            teaching_tips TEXT,
            parent_guidance TEXT,
            FOREIGN KEY (concept_id) REFERENCES concepts(id)
        )""",
    ]

    # Execute statements individually
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    # Define drop statements individually
    drop_statements = [
        "DROP TABLE IF EXISTS concept_metadata",
        "DROP TABLE IF EXISTS quizzes",
        "DROP TABLE IF EXISTS concepts",
        "DROP TABLE IF EXISTS learning_outcomes",
        "DROP TABLE IF EXISTS strand_units",
        "DROP TABLE IF EXISTS strands",
        "DROP TABLE IF EXISTS subjects",
        "DROP TABLE IF EXISTS curriculum_areas",
        "DROP TABLE IF EXISTS school_years",
        "DROP TABLE IF EXISTS education_levels",
    ]

    # Execute drop statements individually
    for statement in drop_statements:
        op.execute(statement)
