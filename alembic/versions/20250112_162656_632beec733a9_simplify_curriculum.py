"""simplify curriculum

Revision ID: 632beec733a9
Revises: acc90e9a87a1
Create Date: 2025-01-12 16:26:56.229281

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "632beec733a9"
down_revision: Union[str, None] = "acc90e9a87a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables in correct order due to dependencies
    drop_statements = [
        "DROP TABLE IF EXISTS quizzes",
        "DROP TABLE IF EXISTS concept_metadata CASCADE",
        "DROP TABLE IF EXISTS concepts CASCADE",
        "DROP TABLE IF EXISTS learning_outcomes CASCADE",
        "DROP TABLE IF EXISTS strand_units CASCADE",
        "DROP TABLE IF EXISTS strands CASCADE",
    ]

    # Drop sequences
    sequence_statements = [
        "DROP SEQUENCE IF EXISTS quizzes_id_seq",
        "DROP SEQUENCE IF EXISTS learning_outcomes_id_seq",
        "DROP SEQUENCE IF EXISTS strand_units_id_seq",
        "DROP SEQUENCE IF EXISTS strands_id_seq",
    ]

    # Create new tables
    create_statements = [
        """CREATE TABLE concepts (
            id SERIAL PRIMARY KEY,
            subject_id INTEGER REFERENCES subjects(id),
            year_id INTEGER REFERENCES school_years(id),
            concept_name VARCHAR(200),
            concept_description TEXT,
            learning_objectives TEXT[],
            strand_reference VARCHAR(200),
            display_order INTEGER
        )""",
        """CREATE TABLE concept_metadata (
            id SERIAL PRIMARY KEY,
            concept_id INTEGER REFERENCES concepts(id),
            why_important JSONB,
            difficulty_stats JSONB,
            parent_guide JSONB,
            real_world JSONB,
            learning_path JSONB,
            time_guide JSONB,
            teaching_tips JSONB,
            common_misconceptions JSONB,
            fun_facts JSONB,
            interactive_ideas JSONB,
            assessment_approaches JSONB,
            irish_language_support JSONB
        )""",
    ]

    # Create indexes
    index_statements = [
        "CREATE INDEX idx_concepts_subject_year ON concepts(subject_id, year_id)",
        "CREATE INDEX idx_concept_metadata_concept ON concept_metadata(concept_id)",
        "CREATE INDEX idx_concepts_display_order ON concepts(subject_id, year_id, display_order)",
    ]

    # Execute all statements in order
    for statement in drop_statements:
        op.execute(statement)

    for statement in sequence_statements:
        op.execute(statement)

    for statement in create_statements:
        op.execute(statement)

    for statement in index_statements:
        op.execute(statement)


def downgrade() -> None:
    # Drop new tables and indexes in reverse order
    statements = [
        "DROP INDEX IF EXISTS idx_concepts_display_order",
        "DROP INDEX IF EXISTS idx_concept_metadata_concept",
        "DROP INDEX IF EXISTS idx_concepts_subject_year",
        "DROP TABLE IF EXISTS concept_metadata",
        "DROP TABLE IF EXISTS concepts",
    ]

    for statement in statements:
        op.execute(statement)
