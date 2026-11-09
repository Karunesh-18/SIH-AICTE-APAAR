"""certificate token

Revision ID: 0008
Revises: 0007
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('certificate_token',
    sa.Column('record_id', sa.String(), nullable=False),
    sa.Column('token_jti', sa.String(length=36), nullable=False),
    sa.Column('issued_by', sa.String(), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['issued_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['record_id'], ['student_record.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_jti')
    )
    op.create_index(op.f('ix_certificate_token_record_id'), 'certificate_token',
                    ['record_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_certificate_token_record_id'), table_name='certificate_token')
    op.drop_table('certificate_token')
