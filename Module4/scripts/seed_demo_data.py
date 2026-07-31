"""Seed synthetic data for exercising/benchmarking the feed and follower
queries (docs/database-design.md's EXPLAIN ANALYZE walkthrough).

Not part of the application or test suite — a one-off dev utility. Uses
generate_series-based bulk INSERTs instead of a Python loop so seeding
tens of thousands of rows takes seconds, not minutes.

Usage: python scripts/seed_demo_data.py [--users N] [--posts N] [--follows N]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from social_media.config.settings import settings  # noqa: E402
from social_media.database.postgres_connection import PostgresConnection  # noqa: E402


def seed(users: int, posts: int, follows: int) -> None:
    pg = PostgresConnection(settings)
    with pg.cursor() as cur:
        print(f"Seeding {users} users...")
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name)
            SELECT 'demo_user_' || i || '@example.com',
                   'not-a-real-hash',
                   'Demo User ' || i
            FROM generate_series(1, %s) AS i
            ON CONFLICT (email) DO NOTHING
            """,
            (users,),
        )

        # Plain volatile expressions (not sub-SELECTs) so Postgres evaluates
        # random() fresh per generated row instead of hoisting an
        # uncorrelated "pick one row" subquery into a single InitPlan
        # value shared by every row. Relies on ids being dense 1..N, true
        # right after a fresh serial-backed insert.
        print(f"Seeding {posts} posts...")
        cur.execute(
            """
            INSERT INTO posts (user_id, content, like_count, comment_count, created_at)
            SELECT (1 + floor(random() * %s))::bigint,
                   'Demo post number ' || i,
                   (random() * 200)::int,
                   (random() * 50)::int,
                   now() - (random() * interval '30 days')
            FROM generate_series(1, %s) AS i
            """,
            (users, posts),
        )

        print(f"Seeding {follows} follow edges...")
        cur.execute(
            """
            INSERT INTO followers (follower_id, followee_id)
            SELECT DISTINCT follower_id, followee_id
            FROM (
                SELECT
                    (1 + floor(random() * %s))::bigint AS follower_id,
                    (1 + floor(random() * %s))::bigint AS followee_id
                FROM generate_series(1, %s)
            ) pairs
            WHERE follower_id <> followee_id
            ON CONFLICT DO NOTHING
            """,
            (users, users, follows),
        )
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=500)
    parser.add_argument("--posts", type=int, default=20000)
    parser.add_argument("--follows", type=int, default=5000)
    args = parser.parse_args()
    seed(args.users, args.posts, args.follows)
