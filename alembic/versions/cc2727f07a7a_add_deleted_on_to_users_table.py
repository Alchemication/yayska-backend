"""add_deleted_on_to_users_table

Revision ID: cc2727f07a7a
Revises: 32e2f7b94f0a
Create Date: 2024-12-21 21:26:24.518792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc2727f07a7a'
down_revision: Union[str, None] = '32e2f7b94f0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('deleted_on', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'deleted_on')
    # ### end Alembic commands ###
