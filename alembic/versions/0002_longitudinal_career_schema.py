"""Add optional longitudinal career fields to contributions (ADR-0008, Task T13.04).

Revision ID: 0002_longitudinal_career_schema
Revises: 0001_initial_governance
Create Date: 2026-10-23

Adds:
- career_start_date: sa.Date (nullable=True)
- last_promotion_date: sa.Date (nullable=True)
- right_censored_exit_flag: sa.Boolean (nullable=True)
to table: app.contributions

Strictly optional, DPDPA-compliant, default null, never required for core compensation prediction.
Enables future re-evaluation of EXP-TRAJ (trajectory velocity) and EXP-SURV (duration models).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_longitudinal_career_schema"
down_revision = "0001_initial_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add optional longitudinal career fields to contributions table."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    schema_app = "app" if is_postgres else None

    with op.batch_alter_table("contributions", schema=schema_app) as batch_op:
        batch_op.add_column(sa.Column("career_start_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("last_promotion_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("right_censored_exit_flag", sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Drop longitudinal career fields from contributions table."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    schema_app = "app" if is_postgres else None

    with op.batch_alter_table("contributions", schema=schema_app) as batch_op:
        batch_op.drop_column("right_censored_exit_flag")
        batch_op.drop_column("last_promotion_date")
        batch_op.drop_column("career_start_date")
