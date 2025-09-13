"""Fix Leave model FK to LeaveType

Revision ID: 4233145d26f6
Revises: 4bf5366010d8
Create Date: 2025-09-13 12:58:22.492879
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4233145d26f6'
down_revision = '4bf5366010d8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('leave', schema=None) as batch_op:
        batch_op.add_column(sa.Column('leave_type_id', sa.Integer(), nullable=False))
        # ✅ Give the constraint a proper name
        batch_op.create_foreign_key(
            "fk_leave_leave_type_id",  # custom name
            "leave_type",              # target table
            ["leave_type_id"],         # source column
            ["id"]                     # target column
        )

    with op.batch_alter_table('leave_type', schema=None) as batch_op:
        batch_op.drop_column('max_days')


def downgrade():
    with op.batch_alter_table('leave_type', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_days', sa.INTEGER(), nullable=True))

    with op.batch_alter_table('leave', schema=None) as batch_op:
        # ✅ Drop the constraint using its name
        batch_op.drop_constraint("fk_leave_leave_type_id", type_="foreignkey")
        batch_op.drop_column('leave_type_id')
