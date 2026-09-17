ALTER TABLE companies
    DROP COLUMN IF EXISTS trustpilot_rating,
    DROP COLUMN IF EXISTS trustpilot_review_count,
    DROP COLUMN IF EXISTS trustpilot_fetched_at,
    DROP COLUMN IF EXISTS ai_needs,
    DROP COLUMN IF EXISTS ai_summary,
    DROP COLUMN IF EXISTS ai_analyzed_at;
