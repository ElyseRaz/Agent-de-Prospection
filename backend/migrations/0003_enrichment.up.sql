ALTER TABLE companies
    ADD COLUMN trustpilot_rating REAL,
    ADD COLUMN trustpilot_review_count INTEGER,
    ADD COLUMN trustpilot_fetched_at TIMESTAMPTZ,
    ADD COLUMN ai_needs JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN ai_summary TEXT,
    ADD COLUMN ai_analyzed_at TIMESTAMPTZ;
