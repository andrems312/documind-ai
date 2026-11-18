"""Prova que as políticas RLS isolam os usuários no nível do banco (segunda camada de defesa).

O backend já filtra por `user_id` na aplicação (primeira camada) e conecta como dono, que
ignora RLS. Aqui assumimos um papel SEM privilégios e com o claim `sub` de um usuário para
confirmar que, mesmo assim, só as linhas desse usuário ficam visíveis.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text

_INSERT_DOC = text(
    "INSERT INTO documents (id, user_id, title, original_filename, storage_path, "
    "file_size, sha256, status) "
    "VALUES (:id, :uid, 't', 'f.pdf', :sp, 1, :sha, 'ready')"
)


async def test_rls_isolates_users_at_database_level(integration_app) -> None:
    engine = integration_app.state.engine
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    doc_a, doc_b = uuid.uuid4(), uuid.uuid4()

    # Como dono (bypassa RLS): cria o papel de teste e os dados de dois usuários.
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rls_tester') "
                "THEN CREATE ROLE rls_tester NOLOGIN; END IF; END $$;"
            )
        )
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO rls_tester"))
        await conn.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rls_tester"
            )
        )
        for uid in (user_a, user_b):
            await conn.execute(text("INSERT INTO profiles (id) VALUES (:id)"), {"id": uid})
        await conn.execute(
            _INSERT_DOC,
            {"id": doc_a, "uid": user_a, "sp": f"{user_a}/{doc_a}.pdf", "sha": "a" * 64},
        )
        await conn.execute(
            _INSERT_DOC,
            {"id": doc_b, "uid": user_b, "sp": f"{user_b}/{doc_b}.pdf", "sha": "b" * 64},
        )

    # Como papel sem privilégios, com o claim do usuário A: RLS deve esconder o documento de B.
    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL ROLE rls_tester"))
        await conn.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps({"sub": str(user_a)})},
        )
        visible = (await conn.execute(text("SELECT user_id FROM documents"))).scalars().all()
        other = await conn.execute(
            text("SELECT count(*) FROM documents WHERE user_id = :u"), {"u": user_b}
        )

    assert user_a in visible
    assert user_b not in visible, "RLS deveria esconder os documentos de outro usuário"
    assert other.scalar() == 0
