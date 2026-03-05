"""add email to jobs

Revision ID: b3c4d5e6f7a8
Revises: 0faf9f1ff9e0
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = '0faf9f1ff9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('jobs', sa.Column('email', sa.String(), nullable=True))


def downgrade():
    op.drop_column('jobs', 'email')
