-- Normalized (3NF) schema for the social media platform.
-- Idempotent: safe to run on every app startup, and safe to re-run by hand.
--
-- This is the canonical DDL — the app loads this exact file on startup
-- (see src/social_media/database/postgres_connection.py). To apply it
-- directly:
--   psql -U postgres -d social_media -f sql/ddl.sql
-- See docs/database-design.md for the ER diagram, normalization rationale,
-- indexing strategy, and measured EXPLAIN ANALYZE output.

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    bio TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    follower_count INTEGER NOT NULL DEFAULT 0,
    following_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);

CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    like_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Drives the feed query: WHERE user_id = ANY(...) ORDER BY created_at DESC.
CREATE INDEX IF NOT EXISTS idx_posts_user_created ON posts (user_id, created_at DESC);
-- Partial index for the common "recent, non-deleted" scan shape.
CREATE INDEX IF NOT EXISTS idx_posts_feed ON posts (created_at DESC) WHERE NOT is_deleted;

CREATE TABLE IF NOT EXISTS comments (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts (id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_comment_id BIGINT REFERENCES comments (id) ON DELETE CASCADE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_post_created ON comments (post_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comments_user ON comments (user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments (parent_comment_id);

-- Composite PK (follower_id, followee_id) is itself a B-tree index covering
-- "who do I follow" lookups. The explicit index below covers the reverse
-- "who follows me" direction — two composite B-tree indexes on this table.
CREATE TABLE IF NOT EXISTS followers (
    follower_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    followee_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id),
    CHECK (follower_id <> followee_id)
);
CREATE INDEX IF NOT EXISTS idx_followers_followee_follower ON followers (followee_id, follower_id);

CREATE TABLE IF NOT EXISTS likes (
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    post_id BIGINT NOT NULL REFERENCES posts (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_post ON likes (post_id);

-- Semi-structured post metadata (tags, location) — deliberately kept out of
-- the normalized `posts` table since it's optional/variable-shape.
CREATE TABLE IF NOT EXISTS post_metadata (
    post_id BIGINT PRIMARY KEY REFERENCES posts (id) ON DELETE CASCADE,
    metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_post_metadata_gin ON post_metadata USING GIN (metadata);
