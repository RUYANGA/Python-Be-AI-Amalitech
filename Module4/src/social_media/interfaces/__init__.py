"""Interface contracts — abstractions the rest of the application depends on.

Repository interfaces live in repositories.py, service interfaces in
services.py. Concrete implementations stay out of this package.
"""

from social_media.interfaces.repositories import (
    IActivityLogRepository,
    ICommentRepository,
    IFollowerRepository,
    ILikeRepository,
    IPostRepository,
    IRepository,
    IUserRepository,
)
from social_media.interfaces.services import (
    IActivityLogService,
    ICommentService,
    IFollowService,
    ILikeService,
    IPostService,
    IUserService,
)

__all__ = [
    "IActivityLogRepository",
    "IActivityLogService",
    "ICommentRepository",
    "ICommentService",
    "IFollowerRepository",
    "IFollowService",
    "ILikeRepository",
    "ILikeService",
    "IPostRepository",
    "IPostService",
    "IRepository",
    "IUserRepository",
    "IUserService",
]
