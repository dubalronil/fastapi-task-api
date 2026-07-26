"""tighten task column types and drop redundant index

Revision ID: 01f2f0cc6e34
Revises: 027a2d1492f6
Create Date: 2026-07-26 16:34:14.824750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01f2f0cc6e34'
down_revision: Union[str, Sequence[str], None] = '027a2d1492f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The primary key is already uniquely indexed, so this second index on the
    # same column only cost writes.
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')

    # Written by hand: autogenerate does not detect an unbounded VARCHAR
    # becoming VARCHAR(n), with or without compare_type, so it produced an
    # empty diff for both of these.
    #
    # Any row longer than the new limit makes this fail, which is what we want
    # — truncating silently would lose data. The API has capped these lengths
    # since before the columns had data, so nothing should be over.
    op.alter_column(
        'tasks', 'title', type_=sa.String(200), existing_nullable=False
    )
    op.alter_column(
        'tasks', 'description', type_=sa.String(2000), existing_nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'tasks', 'description', type_=sa.String(), existing_nullable=True
    )
    op.alter_column('tasks', 'title', type_=sa.String(), existing_nullable=False)
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
