"""Initial schema migration: organizations, users, projects, documents, qc_runs, qc_findings, finding_feedback, audit_logs.

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-25 18:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('plan_tier', sa.String(50), nullable=False, server_default='PAY_PER_CHECK'),
        sa.Column('credits_remaining', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='INSPECTOR'),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_users_org', 'users', ['organization_id'])
    op.create_index('idx_users_email', 'users', ['email'])

    # 3. Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_projects_org', 'projects', ['organization_id'])

    # 4. Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploaded_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('sha256_checksum', sa.String(64), nullable=False),
        sa.Column('storage_path', sa.String(512), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='UPLOADED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_documents_org', 'documents', ['organization_id'])
    op.create_index('idx_doc_org_checksum', 'documents', ['organization_id', 'sha256_checksum'])

    # 5. QC Runs
    op.create_table(
        'qc_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('initiated_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('overall_status', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('checks_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checks_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checks_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checks_review', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('prompt_version', sa.String(50), nullable=False),
        sa.Column('rules_version', sa.String(50), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('token_usage_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_qc_runs_org', 'qc_runs', ['organization_id'])
    op.create_index('idx_qc_runs_doc', 'qc_runs', ['document_id'])

    # 6. QC Findings
    op.create_table(
        'qc_findings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('qc_run_id', sa.String(36), sa.ForeignKey('qc_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('finding_code', sa.String(20), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('confidence_level', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('location_bbox', sa.JSON(), nullable=True),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('requirement_text', sa.Text(), nullable=False),
        sa.Column('standard_citation', sa.String(255), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_qc_findings_run', 'qc_findings', ['qc_run_id'])

    # 7. Finding Feedback
    op.create_table(
        'finding_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('finding_id', sa.String(36), sa.ForeignKey('qc_findings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('feedback_status', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_feedback_finding', 'finding_feedback', ['finding_id'])

    # 8. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_audit_org_created', 'audit_logs', ['organization_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('finding_feedback')
    op.drop_table('qc_findings')
    op.drop_table('qc_runs')
    op.drop_table('documents')
    op.drop_table('projects')
    op.drop_table('users')
    op.drop_table('organizations')
