-- Topics table: one row per post, assigned LDA topic
CREATE TABLE IF NOT EXISTS topics (
    id           SERIAL PRIMARY KEY,
    post_id      VARCHAR(20) UNIQUE NOT NULL,
    subreddit    VARCHAR(100),
    topic_id     INTEGER,
    topic_words  TEXT,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Entities table: one row per entity extracted from a post
CREATE TABLE IF NOT EXISTS entities (
    id           SERIAL PRIMARY KEY,
    post_id      VARCHAR(20) NOT NULL,
    entity_text  TEXT,
    entity_label VARCHAR(20),
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast dashboard queries
CREATE INDEX IF NOT EXISTS idx_topics_topic_id    ON topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_topics_subreddit   ON topics(subreddit);
CREATE INDEX IF NOT EXISTS idx_entities_label     ON entities(entity_label);
CREATE INDEX IF NOT EXISTS idx_entities_post_id   ON entities(post_id);
CREATE INDEX IF NOT EXISTS idx_entities_processed ON entities(processed_at);
