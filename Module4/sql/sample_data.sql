-- Small, readable sample dataset for reviewing/grading the schema by hand.
-- (For a large synthetic dataset to benchmark queries, see
-- scripts/seed_demo_data.py — that one generates thousands of rows via
-- generate_series; this one is a handful of realistic, hand-picked rows.)
--
-- Run against a freshly-created schema (fresh BIGSERIAL sequences, ids
-- start at 1) — apply sql/ddl.sql first:
--   psql -U postgres -d social_media -f sql/ddl.sql
--   psql -U postgres -d social_media -f sql/sample_data.sql
--
-- password_hash values below are placeholders, not valid bcrypt hashes —
-- this dataset is for querying/browsing, not interactive login.

BEGIN;

INSERT INTO users (email, password_hash, full_name, bio) VALUES
    ('alice@example.com', '$2b$12$samplehashsamplehashsamplehashsampleh', 'Alice Nakato', 'Backend engineer. Coffee-powered.'),
    ('bob@example.com',   '$2b$12$samplehashsamplehashsamplehashsampleh', 'Bob Mugisha',  'Photographer and traveler.'),
    ('carol@example.com', '$2b$12$samplehashsamplehashsamplehashsampleh', 'Carol Atim',   NULL),
    ('dave@example.com',  '$2b$12$samplehashsamplehashsamplehashsampleh', 'Dave Okello',  'Building things with Postgres.'),
    ('erin@example.com',  '$2b$12$samplehashsamplehashsamplehashsampleh', 'Erin Namono',  'Just here for the memes.');
-- ids: alice=1, bob=2, carol=3, dave=4, erin=5

INSERT INTO posts (user_id, content, created_at) VALUES
    (1, 'Just deployed my first FastAPI service to production!',                  now() - interval '5 days'),
    (1, 'PostgreSQL composite indexes are underrated.',                           now() - interval '3 days'),
    (2, 'Sunset over Lake Victoria tonight.',                                     now() - interval '4 days'),
    (2, 'New camera lens arrived, time to shoot.',                                now() - interval '1 day'),
    (3, 'Reading up on 3NF and denormalization trade-offs.',                      now() - interval '2 days'),
    (4, 'ROW_NUMBER() window functions beat OFFSET pagination every time.',       now() - interval '6 hours'),
    (4, 'Normalized follow model today: one INSERT, the composite PK does the rest.',  now() - interval '2 hours'),
    (5, 'Lurking as usual.',                                                      now() - interval '30 minutes');
-- ids: 1..8, in the order above

INSERT INTO post_metadata (post_id, metadata) VALUES
    (2, '{"tags": ["postgresql", "indexes", "performance"], "location": null}'),
    (3, '{"tags": ["photography"], "location": "Entebbe, Uganda"}'),
    (6, '{"tags": ["sql", "postgresql"], "location": null}');

-- Top-level comments (ids 1..3 in this order)
INSERT INTO comments (post_id, user_id, content, created_at) VALUES
    (1, 2, 'Congrats! What stack are you using?',                     now() - interval '4 days'),
    (1, 3, 'Nice milestone.',                                         now() - interval '4 days'),
    (2, 4, 'Composite indexes saved me so much pain in production.',  now() - interval '2 days');

-- Threaded reply to comment 1 ("What stack are you using?")
INSERT INTO comments (post_id, user_id, content, parent_comment_id, created_at) VALUES
    (1, 1, 'FastAPI + Postgres + Redis — same stack as this project, actually.', 1, now() - interval '4 days' + interval '1 hour');

INSERT INTO followers (follower_id, followee_id) VALUES
    (1, 2), (1, 4),
    (2, 1), (2, 4),
    (3, 1), (3, 2), (3, 4),
    (4, 1),
    (5, 1), (5, 2), (5, 3), (5, 4);

INSERT INTO likes (user_id, post_id) VALUES
    (2, 1), (3, 1), (4, 1), (5, 1),
    (1, 3), (5, 3),
    (2, 6), (3, 6),
    (1, 7), (2, 7), (3, 7);

-- Recompute the denormalized like/comment counters from the relationships
-- just inserted, rather than hand-counting them — this is exactly what the
-- like/comment services do incrementally in application code; here we derive
-- them in bulk so the sample data is internally consistent regardless of how
-- these INSERTs above get edited later.
-- (users carries no follower/following counters: those are derived from the
-- followers table at query time.)

UPDATE posts p SET
    like_count    = (SELECT count(*) FROM likes l WHERE l.post_id = p.id),
    comment_count = (SELECT count(*) FROM comments c WHERE c.post_id = p.id AND NOT c.is_deleted);

COMMIT;
