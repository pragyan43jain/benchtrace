-- Unknown legacy vectors are never compared to a newly pinned model.
ALTER TABLE document_chunks ADD COLUMN embedding_version text NOT NULL DEFAULT 'unknown';
ALTER TABLE knowledge_entries ADD COLUMN embedding_version text NOT NULL DEFAULT 'unknown';
