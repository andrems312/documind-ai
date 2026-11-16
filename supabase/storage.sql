-- Bucket privado para os PDFs dos usuários. Execute no SQL Editor do Supabase.
-- Caminho dos objetos: <user_id>/<document_id>.pdf

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 26214400, array['application/pdf'])
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Cada usuário só enxerga/gerencia objetos dentro da própria pasta.
drop policy if exists "documents_owner_select" on storage.objects;
create policy "documents_owner_select" on storage.objects for select
  using (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "documents_owner_insert" on storage.objects;
create policy "documents_owner_insert" on storage.objects for insert
  with check (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "documents_owner_delete" on storage.objects;
create policy "documents_owner_delete" on storage.objects for delete
  using (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);
