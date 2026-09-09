"""Add soft-deletable conversations.

Revision ID: d8f2a9c1e741
Revises: b444fa28aa71
"""
from alembic import op
import sqlalchemy as sa

revision = "d8f2a9c1e741"
down_revision = "b444fa28aa71"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_conversations_deleted", "conversations", ["deleted"])
    op.execute("""
        INSERT INTO conversations (session_id, title, deleted, created_at, updated_at)
        SELECT session_id,
               LEFT(MIN(message), 200),
               FALSE,
               MIN(timestamp),
               MAX(timestamp)
        FROM chat_messages
        GROUP BY session_id
    """)


def downgrade():
    op.drop_index("ix_conversations_deleted", table_name="conversations")
    op.drop_table("conversations")

