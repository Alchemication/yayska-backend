"""init schema

Revision ID: 3a36c9c790b6
Revises: 
Create Date: 2024-12-22 20:50:55.624499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a36c9c790b6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('education_levels',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_education_levels_name'), 'education_levels', ['name'], unique=False)
    op.create_table('subjects',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=True),
    sa.Column('last_name', sa.String(length=50), nullable=True),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('school_years',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('education_level_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('short_name', sa.String(length=20), nullable=False),
    sa.Column('order_sequence', sa.Integer(), nullable=False),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['education_level_id'], ['education_levels.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('strands',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('learning_outcomes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('strand_id', sa.Integer(), nullable=False),
    sa.Column('school_year_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['school_year_id'], ['school_years.id'], ),
    sa.ForeignKeyConstraint(['strand_id'], ['strands.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('topics',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('learning_outcome_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('sequence_order', sa.Integer(), nullable=False),
    sa.Column('difficulty_level', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='difficultylevel'), nullable=False),
    sa.Column('prerequisites', sa.Text(), nullable=True),
    sa.Column('teaching_methodology', sa.Text(), nullable=True),
    sa.Column('required_resources', sa.Text(), nullable=True),
    sa.Column('learning_style', sa.Enum('VISUAL', 'AUDITORY', 'KINESTHETIC', 'MIXED', name='learningstyle'), nullable=False),
    sa.Column('assessment_type', sa.String(length=50), nullable=True),
    sa.Column('practice_time_recommended', sa.Integer(), nullable=True),
    sa.Column('is_core', sa.Boolean(), nullable=False),
    sa.Column('curriculum_notes', sa.Text(), nullable=True),
    sa.Column('created_on', sa.DateTime(), nullable=False),
    sa.Column('updated_on', sa.DateTime(), nullable=True),
    sa.Column('deleted_on', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['learning_outcome_id'], ['learning_outcomes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('topics')
    op.drop_table('learning_outcomes')
    op.drop_table('strands')
    op.drop_table('school_years')
    op.drop_table('users')
    op.drop_table('subjects')
    op.drop_index(op.f('ix_education_levels_name'), table_name='education_levels')
    op.drop_table('education_levels')
    # ### end Alembic commands ###
