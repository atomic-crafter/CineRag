CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    file_id      TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    s3_key       TEXT,
    status       TEXT NOT NULL DEFAULT 'pending',
    chunk_count  INTEGER DEFAULT 0,
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    file_id      TEXT NOT NULL REFERENCES documents(file_id) ON DELETE CASCADE,
    chunk_index  INTEGER NOT NULL,
    page_number  INTEGER,
    chunk_text   TEXT NOT NULL,
    embedding    VECTOR(384) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
