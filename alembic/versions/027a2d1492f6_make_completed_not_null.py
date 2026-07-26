"""make completed not null

Revision ID: 027a2d1492f6
Revises: 341af2ad4893
Create Date: 2026-07-26 14:07:11.226903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '027a2d1492f6'
down_revision: Union[str, Sequence[str], None] = '341af2ad4893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill first. Autogenerate can read the schema but not the rows, so it
    # doesn't know some already have NULL here. Without this the ALTER fails.
    op.execute("UPDATE tasks SET completed = 0 WHERE completed IS NULL")

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('completed',
               existing_type=sa.BOOLEAN(),
               nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.alter_column('completed',
               existing_type=sa.BOOLEAN(),
               nullable=True)
