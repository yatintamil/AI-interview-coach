-- Database initialization script for pgvector and candidate profile tables
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure vector cosine index is enabled on resume_chunks if table exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'resume_chunks') THEN
        CREATE INDEX IF NOT EXISTS idx_resume_chunks_embedding 
        ON resume_chunks USING hnsw (embedding vector_cosine_ops);
    END IF;
END $$;
