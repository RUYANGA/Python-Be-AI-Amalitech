"""Repository contracts — re-exported from the interfaces package.

Kept as a thin compatibility module so services, repositories, and tests
can keep importing from social_media.repositories.base. The canonical
definitions now live in social_media/interfaces/repositories.py.
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

__all__ = [
    "IActivityLogRepository",
    "ICommentRepository",
    "IFollowerRepository",
    "ILikeRepository",
    "IPostRepository",
    "IRepository",
    "IUserRepository",
]
