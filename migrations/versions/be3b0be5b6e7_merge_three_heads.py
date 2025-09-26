"""merge three heads

Revision ID: be3b0be5b6e7
Revises: 3790e4b330e5, 681775dffa8c, 82b3ee1248a5
Create Date: 2025-09-22 13:19:43.288660

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be3b0be5b6e7'
down_revision = ('3790e4b330e5', '681775dffa8c', '82b3ee1248a5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
