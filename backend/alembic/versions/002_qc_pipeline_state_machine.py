"""Add QC pipeline state machine columns: pipeline_status, current_step, progress_percent, error_message.

Revision ID: 002_qc_pipeline
Revises: 001_initial
Create Date: 2026-09-25 23:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_qc_pipeline'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('qc_runs', sa.Column('pipeline_status', sa.String(50), nullable=False, server_default='QUEUED'))
    op.add_column('qc_runs', sa.Column('current_step', sa.String(50), nullable=True, server_default='QUEUED'))
    op.add_column('qc_runs', sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('qc_runs', sa.Column('error_message', sa.Text(), nullable=True))
    op.create_index('idx_qc_runs_pipeline_status', 'qc_runs', ['pipeline_status'])


def downgrade() -> None:
    op.drop_index('idx_qc_runs_pipeline_status', table_name='qc_runs')
    op.drop_column('qc_runs', 'error_message')
    op.drop_column('qc_runs', 'progress_percent')
    op.drop_column('qc_runs', 'current_step')
    op.drop_column('qc_runs', 'pipeline_status')
