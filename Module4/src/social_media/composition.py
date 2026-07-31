"""Composition root — wires all dependencies together."""

from social_media.cache.redis_connection import RedisConnection
from social_media.config.settings import settings
from social_media.database.mongodb_connection import MongoConnection
from social_media.database.postgres_connection import PostgresConnection
from social_media.repositories.mongo_repos import ActivityLogRepository
from social_media.repositories.postgres_metadata_repo import PostMetadataRepository
from social_media.repositories.postgres_repos import (
    CommentRepository,
    FollowerRepository,
    LikeRepository,
    PostRepository,
    UserRepository,
)
from social_media.services.activity_log_service import ActivityLogService
from social_media.services.interaction_service import (
    CommentService,
    FollowService,
    LikeService,
)
from social_media.services.post_service import PostService
from social_media.services.user_service import UserService
from social_media.utils.security import PasswordHasher, PasswordValidator


def build_services():
    """Dependency injection wiring — the only place concrete types meet."""
    pg = PostgresConnection(settings)

    user_repo = UserRepository(pg)
    post_repo = PostRepository(pg)
    comment_repo = CommentRepository(pg)
    follower_repo = FollowerRepository(pg)
    like_repo = LikeRepository(pg)
    metadata_repo = PostMetadataRepository(pg)

    mongo_db = MongoConnection(settings).db
    activity_log = ActivityLogService(ActivityLogRepository(mongo_db))

    redis_conn = RedisConnection(settings)
    cache_client = redis_conn.client

    return {
        "users": UserService(
            user_repo, PasswordHasher(settings.bcrypt_rounds), PasswordValidator()
        ),
        "posts": PostService(
            post_repo,
            follower_repo,
            metadata_repo=metadata_repo,
            cache_client=cache_client,
            activity_log=activity_log,
        ),
        "likes": LikeService(like_repo, post_repo, activity_log=activity_log),
        "comments": CommentService(comment_repo, post_repo, activity_log=activity_log),
        "follows": FollowService(follower_repo, activity_log=activity_log),
        "metadata_repo": metadata_repo,
    }
