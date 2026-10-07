-- Supabase Schema for Prompt Việt (NGU-17)
-- Table: prompts

CREATE EXTENSION IF NOT EXISTS "unaccent";

CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    original_title TEXT NOT NULL,
    original_prompt TEXT NOT NULL,
    language_original TEXT,
    language_detection TEXT,
    vi_title TEXT NOT NULL,
    vi_prompt TEXT NOT NULL,
    translation_status TEXT NOT NULL DEFAULT 'translated',
    source_category TEXT,
    source_tags JSONB DEFAULT '[]'::jsonb,
    category TEXT NOT NULL,
    subcategory TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    search_keywords_vi JSONB DEFAULT '[]'::jsonb,
    use_case TEXT,
    model_type TEXT,
    difficulty TEXT,
    quality_status TEXT NOT NULL DEFAULT 'ok',
    author TEXT,
    source TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for Fast Filtering
CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category);
CREATE INDEX IF NOT EXISTS idx_prompts_subcategory ON prompts(subcategory);
CREATE INDEX IF NOT EXISTS idx_prompts_difficulty ON prompts(difficulty);
CREATE INDEX IF NOT EXISTS idx_prompts_model_type ON prompts(model_type);
CREATE INDEX IF NOT EXISTS idx_prompts_quality_status ON prompts(quality_status);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_prompts_keywords ON prompts USING GIN (search_keywords_vi);

-- Vietnamese Full Text Search (FTS)
-- Generated column combining Vietnamese title, prompt, category, subcategory and use case
ALTER TABLE prompts ADD COLUMN IF NOT EXISTS fts tsvector 
GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(vi_title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(category, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(subcategory, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(use_case, '')), 'C') ||
    setweight(to_tsvector('simple', coalesce(vi_prompt, '')), 'D')
) STORED;

CREATE INDEX IF NOT EXISTS idx_prompts_fts ON prompts USING GIN (fts);

-- Row Level Security (RLS)
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" 
ON prompts 
FOR SELECT 
USING (true);
