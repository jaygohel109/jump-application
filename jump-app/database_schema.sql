-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Tasks table for managing ongoing tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    assigned_to TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Ongoing instructions table for remembering user preferences
CREATE TABLE IF NOT EXISTS ongoing_instructions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    instruction TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Email embeddings table for RAG
CREATE TABLE IF NOT EXISTS email_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email_id TEXT NOT NULL,
    subject TEXT,
    sender TEXT,
    recipient TEXT,
    content TEXT,
    date TIMESTAMP WITH TIME ZONE,
    embedding vector(3072), -- OpenAI text-embedding-3-large dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- HubSpot embeddings table for RAG
CREATE TABLE IF NOT EXISTS hubspot_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    contact_id TEXT,
    contact_email TEXT,
    contact_name TEXT,
    content_type TEXT CHECK (content_type IN ('contact', 'note')),
    content TEXT,
    embedding vector(3072), -- OpenAI text-embedding-3-large dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Calendar embeddings table for RAG
CREATE TABLE IF NOT EXISTS calendar_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id TEXT NOT NULL,
    summary TEXT,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    attendees TEXT[], -- Array of attendee emails
    location TEXT,
    embedding vector(3072), -- OpenAI text-embedding-3-large dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation history table
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_ongoing_instructions_active ON ongoing_instructions(is_active);
CREATE INDEX IF NOT EXISTS idx_ongoing_instructions_category ON ongoing_instructions(category);
CREATE INDEX IF NOT EXISTS idx_email_embeddings_date ON email_embeddings(date);
CREATE INDEX IF NOT EXISTS idx_hubspot_embeddings_type ON hubspot_embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_calendar_embeddings_start ON calendar_embeddings(start_time);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_date ON conversation_history(created_at);

-- Create vector indexes for similarity search
CREATE INDEX IF NOT EXISTS idx_email_embeddings_vector ON email_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_hubspot_embeddings_vector ON hubspot_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_calendar_embeddings_vector ON calendar_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Enable Row Level Security (RLS)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ongoing_instructions ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE hubspot_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- Create policies (for now, allow all operations - you can restrict this later)
CREATE POLICY "Allow all operations on tasks" ON tasks FOR ALL USING (true);
CREATE POLICY "Allow all operations on ongoing_instructions" ON ongoing_instructions FOR ALL USING (true);
CREATE POLICY "Allow all operations on email_embeddings" ON email_embeddings FOR ALL USING (true);
CREATE POLICY "Allow all operations on hubspot_embeddings" ON hubspot_embeddings FOR ALL USING (true);
CREATE POLICY "Allow all operations on calendar_embeddings" ON calendar_embeddings FOR ALL USING (true);
CREATE POLICY "Allow all operations on conversation_history" ON conversation_history FOR ALL USING (true);

-- Create functions for similarity search
CREATE OR REPLACE FUNCTION match_emails(
    query_embedding vector(3072),
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    email_id TEXT,
    subject TEXT,
    sender TEXT,
    recipient TEXT,
    content TEXT,
    date TIMESTAMP WITH TIME ZONE,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        email_embeddings.id,
        email_embeddings.email_id,
        email_embeddings.subject,
        email_embeddings.sender,
        email_embeddings.recipient,
        email_embeddings.content,
        email_embeddings.date,
        1 - (email_embeddings.embedding <=> query_embedding) AS similarity
    FROM email_embeddings
    WHERE 1 - (email_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY email_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION match_hubspot_data(
    query_embedding vector(3072),
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    contact_id TEXT,
    contact_email TEXT,
    contact_name TEXT,
    content_type TEXT,
    content TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hubspot_embeddings.id,
        hubspot_embeddings.contact_id,
        hubspot_embeddings.contact_email,
        hubspot_embeddings.contact_name,
        hubspot_embeddings.content_type,
        hubspot_embeddings.content,
        1 - (hubspot_embeddings.embedding <=> query_embedding) AS similarity
    FROM hubspot_embeddings
    WHERE 1 - (hubspot_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY hubspot_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION match_calendar_events(
    query_embedding vector(3072),
    match_threshold float DEFAULT 0.8,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    event_id TEXT,
    summary TEXT,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    attendees TEXT[],
    location TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        calendar_embeddings.id,
        calendar_embeddings.event_id,
        calendar_embeddings.summary,
        calendar_embeddings.description,
        calendar_embeddings.start_time,
        calendar_embeddings.end_time,
        calendar_embeddings.attendees,
        calendar_embeddings.location,
        1 - (calendar_embeddings.embedding <=> query_embedding) AS similarity
    FROM calendar_embeddings
    WHERE 1 - (calendar_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY calendar_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$; 