"""Schema inicial: extensões, tabelas, índices vetoriais/full-text e políticas RLS.

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.db.base import EMBEDDING_DIM

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")
GEN_UUID = sa.text("gen_random_uuid()")

# Tabelas cujo isolamento por usuário é direto (coluna user_id).
_USER_TABLES = (
    "folders",
    "documents",
    "document_chunks",
    "conversations",
    "analyses",
    "usage_events",
)


def _enum(name: str, *values: str) -> pg.ENUM:
    return pg.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Compatibilidade com Postgres fora do Supabase -------------------------------------
    # No Supabase `auth.uid()` já existe. Em um Postgres comum (docker compose) criamos um
    # equivalente que lê o claim `sub` da configuração `request.jwt.claims`.
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regprocedure('auth.uid()') IS NULL THEN
                CREATE FUNCTION auth.uid() RETURNS uuid
                LANGUAGE sql STABLE AS $fn$
                    SELECT nullif(
                        coalesce(
                            current_setting('request.jwt.claim.sub', true),
                            (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')
                        ),
                        ''
                    )::uuid
                $fn$;
            END IF;
        END $$;
        """
    )

    # --- Enums -------------------------------------------------------------------------------
    for name, values in {
        "document_status": ("uploaded", "processing", "ready", "failed"),
        "job_status": ("queued", "running", "done", "failed"),
        "message_role": ("user", "assistant"),
        "analysis_type": ("summary", "key_info", "comparison"),
        "usage_kind": ("upload", "question", "summary", "key_info", "comparison", "search"),
    }.items():
        pg.ENUM(*values, name=name).create(op.get_bind(), checkfirst=True)

    # --- Tabelas -----------------------------------------------------------------------------
    op.create_table(
        "profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320)),
        sa.Column("full_name", sa.String(120)),
        sa.Column("avatar_url", sa.String(2048)),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
    )

    op.create_table(
        "folders",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("parent_id", UUID, sa.ForeignKey("folders.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("color", sa.String(16)),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
    )
    op.create_index("ix_folders_user_id_name", "folders", ["user_id", "name"])

    op.create_table(
        "documents",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("folder_id", UUID, sa.ForeignKey("folders.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer),
        sa.Column("processed_pages", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status",
            _enum("document_status", "uploaded", "processing", "ready", "failed"),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("error_message", sa.Text),
        sa.Column("processed_at", TS),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
        sa.UniqueConstraint("user_id", "sha256", name="uq_documents_user_id_sha256"),
    )
    op.create_index("ix_documents_user_id_created_at", "documents", ["user_id", "created_at"])
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])

    op.create_table(
        "document_pages",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("char_count", sa.Integer, nullable=False),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_pages_document_page"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "tsv",
            pg.TSVECTOR,
            sa.Computed("to_tsvector('portuguese', content)", persisted=True),
        ),
        sa.Column("metadata", pg.JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk"),
    )
    op.create_index(
        "ix_document_chunks_document_id_page_number",
        "document_chunks",
        ["document_id", "page_number"],
    )
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_document_chunks_tsv", "document_chunks", ["tsv"], postgresql_using="gin")

    op.create_table(
        "processing_jobs",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "status",
            _enum("job_status", "queued", "running", "done", "failed"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("started_at", TS),
        sa.Column("finished_at", TS),
    )
    op.create_index(
        "ix_processing_jobs_status_created_at", "processing_jobs", ["status", "created_at"]
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(160), nullable=False, server_default="Nova conversa"),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
    )
    op.create_index(
        "ix_conversations_user_id_updated_at", "conversations", ["user_id", "updated_at"]
    )

    op.create_table(
        "conversation_documents",
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.PrimaryKeyConstraint("conversation_id", "document_id", name="pk_conversation_documents"),
    )

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", _enum("message_role", "user", "assistant"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
    )
    op.create_index(
        "ix_messages_conversation_id_created_at", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "message_citations",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "message_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("chunk_id", UUID, sa.ForeignKey("document_chunks.id", ondelete="SET NULL")),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("score", sa.Float),
        sa.Column("rank", sa.Integer, nullable=False),
    )

    op.create_table(
        "analyses",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "type", _enum("analysis_type", "summary", "key_info", "comparison"), nullable=False
        ),
        sa.Column("document_ids", pg.ARRAY(UUID), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
    )
    op.create_index("ix_analyses_user_id_created_at", "analyses", ["user_id", "created_at"])

    op.create_table(
        "usage_events",
        sa.Column("id", UUID, primary_key=True, server_default=GEN_UUID),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "kind",
            _enum(
                "usage_kind", "upload", "question", "summary", "key_info", "comparison", "search"
            ),
            nullable=False,
        ),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="SET NULL")),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
    )
    op.create_index("ix_usage_events_user_id_created_at", "usage_events", ["user_id", "created_at"])

    # --- updated_at automático ---------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END $$;
        """
    )
    for table in ("profiles", "folders", "documents", "conversations"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()"
        )

    # --- Row Level Security -------------------------------------------------------------------
    # O backend conecta com um papel que ignora RLS e valida a posse em código; estas políticas
    # protegem os dados contra acesso direto pela API do Supabase (anon/authenticated).
    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY profiles_self ON profiles FOR ALL "
        "USING (id = auth.uid()) WITH CHECK (id = auth.uid())"
    )
    for table in _USER_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner ON {table} FOR ALL "
            f"USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())"
        )

    via_document = (
        "EXISTS (SELECT 1 FROM documents d WHERE d.id = document_id AND d.user_id = auth.uid())"
    )
    via_conversation = (
        "EXISTS (SELECT 1 FROM conversations c "
        "WHERE c.id = conversation_id AND c.user_id = auth.uid())"
    )
    via_message = (
        "EXISTS (SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id "
        "WHERE m.id = message_id AND c.user_id = auth.uid())"
    )
    child_policies = {
        "document_pages": via_document,
        "processing_jobs": via_document,
        "conversation_documents": via_conversation,
        "messages": via_conversation,
        "message_citations": via_message,
    }
    for table, predicate in child_policies.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner ON {table} FOR ALL "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade() -> None:
    for table in (
        "usage_events",
        "analyses",
        "message_citations",
        "messages",
        "conversation_documents",
        "conversations",
        "processing_jobs",
        "document_chunks",
        "document_pages",
        "documents",
        "folders",
        "profiles",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at()")
    for name in ("usage_kind", "analysis_type", "message_role", "job_status", "document_status"):
        pg.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
