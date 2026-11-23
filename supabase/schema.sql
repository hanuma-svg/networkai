-- ==============================================================================
-- NetworkAI Supabase Database Schema
-- Includes pgvector extension, contacts, interactions, and action_queue tables
-- ==============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Helper function for automated updated_at timestamp maintenance
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- Table: contacts
-- Stores professional contacts with pgvector embedding column for semantic search
-- ==============================================================================
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    email TEXT,
    headline TEXT,
    company TEXT,
    linkedin_url TEXT UNIQUE,
    location TEXT,
    -- Default 768 dimensions for Google Gemini text-embedding-004.
    -- Can be modified to 1536 for OpenAI text-embedding-3 or 3072 for Gemini 1.5.
    embedding vector(768),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Trigger for contacts updated_at
DROP TRIGGER IF EXISTS set_contacts_updated_at ON contacts;
CREATE TRIGGER set_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes for contacts
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_linkedin_url ON contacts(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_contacts_embedding_hnsw 
    ON contacts USING hnsw (embedding vector_cosine_ops);

-- ==============================================================================
-- Table: interactions
-- Tracks all messages, connection requests, comments, and meetings with contacts
-- ==============================================================================
CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('message', 'connection_request', 'comment', 'email', 'meeting', 'other')),
    channel TEXT NOT NULL DEFAULT 'linkedin',
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT,
    interaction_date TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for interactions
CREATE INDEX IF NOT EXISTS idx_interactions_contact_id ON interactions(contact_id);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions(interaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(type);

-- ==============================================================================
-- Table: action_queue
-- Queues AI-generated actions (draft comments, connection notes <= 300 chars, follow-ups)
-- awaiting human approval
-- ==============================================================================
CREATE TABLE IF NOT EXISTS action_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('draft_comment', 'connection_note', 'follow_up')),
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_approval' CHECK (status IN ('pending_approval', 'approved', 'rejected', 'executed')),
    scheduled_for TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),

    -- Constraint enforcing LinkedIn connection note limit of 300 characters
    CONSTRAINT connection_note_char_limit CHECK (
        action_type != 'connection_note' OR char_length(content) <= 300
    )
);

-- Trigger for action_queue updated_at
DROP TRIGGER IF EXISTS set_action_queue_updated_at ON action_queue;
CREATE TRIGGER set_action_queue_updated_at
    BEFORE UPDATE ON action_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes for action_queue
CREATE INDEX IF NOT EXISTS idx_action_queue_contact_id ON action_queue(contact_id);
CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue(status);
CREATE INDEX IF NOT EXISTS idx_action_queue_action_type ON action_queue(action_type);
CREATE INDEX IF NOT EXISTS idx_action_queue_scheduled_for ON action_queue(scheduled_for);

-- ==============================================================================
-- Row Level Security (RLS) policies
-- ==============================================================================
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_queue ENABLE ROW LEVEL SECURITY;

-- Allow service role full access by default
CREATE POLICY "Service role full access on contacts"
    ON contacts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on interactions"
    ON interactions FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on action_queue"
    ON action_queue FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
