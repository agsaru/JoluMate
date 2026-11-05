
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

DROP TABLE IF EXISTS refresh_tokens CASCADE;
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for cleanup queries that filter by user_id + expires_at
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);

DROP TABLE IF EXISTS conversations CASCADE;
CREATE TABLE conversations(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for listing conversations by user
CREATE INDEX idx_conversations_user_id ON conversations (user_id, created_at DESC);

DROP TABLE IF EXISTS chats CASCADE;
CREATE TABLE chats (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fetching chat history by conversation
CREATE INDEX idx_chats_conversation_id ON chats (conversation_id, created_at ASC);

DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768),
    filename TEXT,
    page_number INTEGER,
    chunk_index INTEGER,
    start_index INTEGER,
    embedding_model TEXT NOT NULL DEFAULT 'gemini-embedding-001'
);

-- Vector similarity index for RAG search (IVFFlat with cosine distance)
-- Note: Requires at least ~100 rows to be effective; adjust 'lists' as data grows
CREATE INDEX idx_documents_embedding ON documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for filtering documents by user + conversation before vector search
CREATE INDEX idx_documents_user_conversation ON documents (user_id, conversation_id);
CREATE INDEX idx_documents_embedding_model
    ON documents (user_id, conversation_id, embedding_model);
