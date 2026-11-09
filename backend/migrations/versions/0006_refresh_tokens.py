"""refresh tokens

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('refresh_token',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('family_id', sa.String(length=36), nullable=False),
    sa.Column('jti_hash', sa.String(length=64), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('grace_used', sa.Boolean(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('jti_hash')
    )
    with op.batch_alter_table('refresh_token', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_token_family_id'), ['family_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_refresh_token_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('refresh_token', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_refresh_token_user_id'))
        batch_op.drop_index(batch_op.f('ix_refresh_token_family_id'))

    op.drop_table('refresh_token')
