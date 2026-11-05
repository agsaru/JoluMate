-- Add document source metadata and track the embedding model used for each row.
-- Safe to run on an existing database; does not drop or rewrite document data.

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS filename TEXT,
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
    ADD COLUMN IF NOT EXISTS start_index INTEGER,
    ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL
        DEFAULT 'models/text-embedding-004';

CREATE INDEX IF NOT EXISTS idx_documents_embedding_model
    ON documents (user_id, conversation_id, embedding_model);
