"""Professional menu-driven CLI for the social media platform."""

import sys
from pathlib import Path
from typing import Any

_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from social_media.composition import build_services  # noqa: E402
from social_media.exceptions import (  # noqa: E402
    InvalidCredentialsError,
    InvalidEmailError,
    UserAlreadyExistsError,
    WeakPasswordError,
)
from social_media.utils.logger import get_logger  # noqa: E402

log = get_logger("cli")

WIDTH = 62


def _line(ch="─") -> str:
    return ch * WIDTH


def _title(text: str) -> None:
    pad = (WIDTH - len(text) - 2) // 2
    print(f"\n{'═' * WIDTH}")
    print(f"{' ' * pad}{text}{' ' * (WIDTH - len(text) - 2 - pad)}")
    print(f"{'═' * WIDTH}")


def _menu(title: str, items: list[str]) -> int | None:
    print(f"\n  {title}")
    print(f"  {_line('─')}")
    for i, item in enumerate(items, 1):
        print(f"    {i:>2}. {item}")
    print(f"    {'─' * (WIDTH - 4)}")
    while True:
        try:
            raw = input(f"\n    Choice (1-{len(items)}, 0=back): ").strip()
            if raw == "0":
                return None
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
            print(f"    Invalid choice. Enter 1-{len(items)} or 0.")
        except ValueError:
            print("    Enter a number.")


def _user_label(doc: dict) -> str:
    name = doc.get("full_name") or "???"
    return f"{name} <{doc['email']}>"


def _metadata_line(md: dict | None) -> str:
    if md is None:
        return ""
    parts = []
    if md.get("tags"):
        parts.append(f"🏷 {' '.join(f'#{t}' for t in md['tags'])}")
    if md.get("location"):
        parts.append(f"📍 {md['location']}")
    return " | ".join(parts) if parts else ""


def _post_line(post: dict, user_map: dict, metadata: dict | None = None) -> str:
    author = user_map.get(post["user_id"], {})
    label = _user_label(author) if author else str(post["user_id"])
    md = _metadata_line(metadata)
    lines = [
        f"    [{post['id']}] {post['content']}",
        f"    {label}  ♥ {post.get('like_count', 0)}  "
        f"💬 {post.get('comment_count', 0)}",
    ]
    if md:
        lines.insert(1, f"    {md}")
    return "\n".join(lines)


def _pause() -> None:
    input(f"\n    {'─' * (WIDTH - 4)}\n    Press Enter to continue...")


def _require_user(app: "App") -> bool:
    if not app.user:
        print("\n    You must be logged in to do that.")
        _pause()
        return False
    return True


class App:
    """Application shell — wires services and runs the menu loop."""

    def __init__(self) -> None:
        svc = build_services()
        self.users_svc = svc["users"]
        self.posts_svc = svc["posts"]
        self.likes_svc = svc["likes"]
        self.comments_svc = svc["comments"]
        self.follows_svc = svc["follows"]
        self._metadata_repo = svc["metadata_repo"]
        self._user: dict | None = None

    # -- properties -------------------------------------------------------

    @property
    def user(self) -> dict | None:
        return self._user

    @property
    def uid(self) -> Any:
        return self._user["id"] if self._user else None

    # -- user helpers -----------------------------------------------------

    def _all_users(self) -> list[dict]:
        return list(self.users_svc._users.find({}))

    def _user_map(self) -> dict:
        return {u["id"]: u for u in self._all_users()}

    def _find_user_by_email(self, email: str) -> dict | None:
        return self.users_svc._users.find_by_email(email)

    def _pick_user(self, users: list[dict], title: str) -> dict | None:
        if not users:
            print("\n  No users found.")
            return None
        print(f"\n  {title}")
        print(f"  {_line('─')}")
        for i, u in enumerate(users, 1):
            print(f"    {i:>2}. {_user_label(u)}")
        print(f"    {'─' * (WIDTH - 4)}")
        while True:
            try:
                raw = input(f"\n    Pick a user (1-{len(users)}, 0=back): ").strip()
                if raw == "0":
                    return None
                idx = int(raw) - 1
                if 0 <= idx < len(users):
                    return users[idx]
                print(f"    Invalid choice. Enter 1-{len(users)} or 0.")
            except ValueError:
                print("    Enter a number.")

    # -- post helpers -----------------------------------------------------

    def _enrich_metadata(self, posts: list[dict]) -> dict[Any, dict]:
        pids = [p["id"] for p in posts]
        return self._metadata_repo.find_many(pids)

    def _all_posts(self) -> tuple[list[dict], dict, dict[Any, dict]]:
        posts = list(self.posts_svc._posts.find({}))
        umap = self._user_map()
        meta = self._enrich_metadata(posts)
        return posts, umap, meta

    def _my_posts(self) -> tuple[list[dict], dict, dict[Any, dict]]:
        posts = list(self.posts_svc._posts.find({"user_id": self.uid}))
        umap = self._user_map()
        meta = self._enrich_metadata(posts)
        return posts, umap, meta

    def _pick_post(
        self,
        posts: list[dict],
        umap: dict,
        title: str,
        metadata: dict[Any, dict] | None = None,
    ) -> dict | None:
        if not posts:
            print("\n  No posts found.")
            return None
        metadata = metadata or {}
        print(f"\n  {title}")
        print(f"  {_line('─')}")
        for i, p in enumerate(posts, 1):
            author = umap.get(p["user_id"], {})
            label = _user_label(author) if author else p["user_id"]
            md = _metadata_line(metadata.get(p["id"]))
            print(f"    {i:>2}. {p['content'][:50]}")
            if md:
                print(f"       {md}")
            print(
                f"       {label}  ♥ {p.get('like_count', 0)}  💬 {p.get('comment_count', 0)}"
            )
        print(f"    {'─' * (WIDTH - 4)}")
        while True:
            try:
                raw = input(f"\n    Pick a post (1-{len(posts)}, 0=back): ").strip()
                if raw == "0":
                    return None
                idx = int(raw) - 1
                if 0 <= idx < len(posts):
                    return posts[idx]
                print(f"    Invalid choice. Enter 1-{len(posts)} or 0.")
            except ValueError:
                print("    Enter a number.")

    def _post_action_menu(
        self, post: dict, umap: dict, metadata: dict[Any, dict] | None = None
    ) -> None:
        assert self._user is not None
        metadata = metadata or {}
        is_owner = post["user_id"] == self.uid
        while True:
            _title("Post Actions")
            author = umap.get(post["user_id"], {})
            label = _user_label(author) if author else post["user_id"]
            print(f"  {post['content']}")
            md = _metadata_line(metadata.get(post["id"]))
            if md:
                print(f"  {md}")
            print(
                f"  {label}  ♥ {post.get('like_count', 0)}  💬 {post.get('comment_count', 0)}"
            )
            items = ["Like", "Unlike", "Comment", "View Comments"]
            if is_owner:
                items.extend(["Edit", "Delete"])
            idx = _menu("Post Actions", items)
            if idx is None:
                return
            if idx == 0:
                _title("Like Post")
                if self.likes_svc.like(self.uid, post["id"]):
                    log.info("Post liked by %s", self._user["email"])
                    print("  You liked the post.")
                    post["like_count"] = post.get("like_count", 0) + 1
                else:
                    print("  You already liked that post.")
            elif idx == 1:
                _title("Unlike Post")
                if self.likes_svc.unlike(self.uid, post["id"]):
                    log.info("Post unliked by %s", self._user["email"])
                    print("  You unliked the post.")
                    post["like_count"] = max(0, post.get("like_count", 0) - 1)
                else:
                    print("  You hadn't liked that post.")
            elif idx == 2:
                _title("Comment")
                content = input("  Comment: ").strip()
                if content:
                    doc = self.comments_svc.add(post["id"], self.uid, content)
                    log.info("Comment added by %s", self._user["email"])
                    print(f"\n  Comment added! ID: {doc['id']}")
                    post["comment_count"] = post.get("comment_count", 0) + 1
                else:
                    print("\n  Comment cannot be empty.")
            elif idx == 3:
                _title("Comments")
                comments = self.comments_svc.for_post(post["id"])
                if not comments:
                    print("  No comments yet.")
                else:
                    for c in comments:
                        author = umap.get(c["user_id"], {})
                        label = _user_label(author) if author else c["user_id"]
                        print(f"\n  [{c['id']}] {label}")
                        print(f"  {c['content']}")
            elif idx == 4 and is_owner:
                _title("Edit Post")
                new_content = input("  New content: ").strip()
                if new_content:
                    print("  Metadata (optional, press Enter to skip):")
                    tags_raw = input("    Tags (comma-separated): ").strip()
                    tags = (
                        [t.strip() for t in tags_raw.split(",") if t.strip()]
                        if tags_raw
                        else None
                    )
                    location = input("    Location: ").strip() or None
                    updated = self.posts_svc.update(
                        post["id"], new_content, tags=tags, location=location
                    )
                    if updated:
                        post["content"] = updated["content"]
                        log.info("Post edited by %s", self._user["email"])
                        print("  Post updated.")
                    else:
                        print("  Post not found.")
                else:
                    print("  Content cannot be empty.")
            elif idx == 5 and is_owner:
                self.posts_svc.soft_delete(post["id"])
                log.info("Post deleted by %s", self._user["email"])
                print("  Post deleted.")
                return
            _pause()

    # ====================================================================
    # MAIN LOOP
    # ====================================================================

    def run(self) -> None:
        while True:
            self._main_menu()

    def _main_menu(self) -> None:
        status = _user_label(self._user) if self._user else "Not logged in"
        print(f"\n{'╔' + '═' * (WIDTH - 2) + '╗'}")
        print(f"║{' ' * (WIDTH - 2)}║")
        print(f"║{'SOCIAL MEDIA CLI'.center(WIDTH - 2)}║")
        print(f"║{'─' * (WIDTH - 2)}║")
        print(f"║{status.center(WIDTH - 2)}║")
        print(f"║{' ' * (WIDTH - 2)}║")
        print(f"{'╚' + '═' * (WIDTH - 2) + '╝'}")

        if self._user:
            items = [
                "Profile & Users",
                "Posts",
                "Follows",
                "Timeline",
                "Logout",
            ]
            idx = _menu("Main Menu", items)
            if idx is None:
                return
            {
                0: self._profile_menu,
                1: self._posts_menu,
                2: self._follows_menu,
                3: self._timeline_menu,
                4: self._logout,
            }[idx]()
        else:
            items = ["Login", "Register"]
            idx = _menu("Main Menu", items)
            if idx is None:
                return
            if idx == 0:
                self._login()
            else:
                self._register()

    # ====================================================================
    # AUTH
    # ====================================================================

    def _login(self) -> None:
        _title("Login")
        email = input("  Email    : ").strip()
        password = input("  Password : ").strip()
        try:
            self._user = self.users_svc.authenticate(email, password)
            assert self._user is not None
            log.info("User logged in: %s", email)
            print(f"\n  Welcome back, {_user_label(self._user)}!")
        except InvalidCredentialsError:
            log.warning("Failed login attempt for %s", email)
            print("\n  Invalid email or password.")
        _pause()

    def _register(self) -> None:
        _title("Register")
        email = input("  Email     : ").strip()
        password = input("  Password  : ").strip()
        name = input("  Full name : ").strip() or None
        try:
            doc = self.users_svc.register(email, password, name)
            log.info("User registered: %s", email)
            print(f"\n  Registered {_user_label(doc)}.")
        except UserAlreadyExistsError:
            log.warning("Registration failed (exists): %s", email)
            print(f"\n  User already exists: {email}")
        except InvalidEmailError as e:
            log.warning("Registration failed (invalid email): %s", email)
            print(f"\n  {e}")
        except WeakPasswordError as e:
            log.warning("Registration failed (weak password): %s", email)
            print(f"\n  {e}")
        _pause()

    def _logout(self) -> None:
        log.info("User logged out: %s", self._user["email"] if self._user else "?")
        self._user = None
        print("\n  Logged out.")
        _pause()

    # ====================================================================
    # PROFILE
    # ====================================================================

    def _profile_menu(self) -> None:
        if not _require_user(self):
            return
        items = ["My Profile", "List All Users", "Search User by Email"]
        idx = _menu("Profile & Users", items)
        if idx is None:
            return
        if idx == 0:
            _title("My Profile")
            assert self._user is not None
            u = self._user
            print(f"  Name      : {u.get('full_name') or '—'}")
            print(f"  Email     : {u['email']}")
            print(f"  User ID   : {u['id']}")
            print(f"  Active    : {u.get('is_active', True)}")
        elif idx == 1:
            _title("All Users")
            for u in self._all_users():
                print(f"  • {_user_label(u)}")
        elif idx == 2:
            _title("Search User")
            email = input("  Email: ").strip()
            doc = self._find_user_by_email(email)
            if doc:
                print(f"\n  Found: {_user_label(doc)}")
            else:
                print("\n  No user found with that email.")
        _pause()

    # ====================================================================
    # POSTS
    # ====================================================================

    def _posts_menu(self) -> None:
        if not _require_user(self):
            return
        items = ["Create Post", "Browse All Posts", "My Posts", "Trending Posts"]
        idx = _menu("Posts", items)
        if idx is None:
            return
        if idx == 0:
            _title("Create Post")
            content = input("  Content: ").strip()
            if content:
                print("  Metadata (optional, press Enter to skip):")
                tags_raw = input("    Tags (comma-separated): ").strip()
                tags = (
                    [t.strip() for t in tags_raw.split(",") if t.strip()]
                    if tags_raw
                    else None
                )
                location = input("    Location: ").strip() or None
                doc = self.posts_svc.create(
                    self.uid, content, tags=tags, location=location
                )
                snippet = f'"{content[:40]}{"..." if len(content) > 40 else ""}"'
                assert self._user is not None
                log.info("Post created by %s: %s", self._user["email"], snippet)
                print(f"\n  Posted! ID: {doc['id']}")
            else:
                print("\n  Content cannot be empty.")
        elif idx == 1:
            posts, umap, meta = self._all_posts()
            post = self._pick_post(posts, umap, "All Posts", meta)
            if post:
                self._post_action_menu(post, umap, meta)
        elif idx == 2:
            posts, umap, meta = self._my_posts()
            post = self._pick_post(posts, umap, "My Posts", meta)
            if post:
                self._post_action_menu(post, umap, meta)
        elif idx == 3:
            _title("Trending Posts")
            umap = self._user_map()
            trending = self.posts_svc.trending()
            if not trending:
                print("  Nothing trending yet.")
            else:
                for rank, p in enumerate(trending, 1):
                    author = umap.get(p["user_id"], {})
                    label = _user_label(author) if author else p["user_id"]
                    print(f"\n  {rank:>2}. {p['content'][:50]}  (score {p['score']})")
                    print(
                        f"      {label}  ♥ {p['like_count']}  💬 {p['comment_count']}"
                    )
        _pause()

    # ====================================================================
    # FOLLOWS
    # ====================================================================

    def _follows_menu(self) -> None:
        if not _require_user(self):
            return
        assert self._user is not None
        items = ["Follow a User", "Unfollow a User", "Who I Follow", "My Followers"]
        idx = _menu("Follows", items)
        if idx is None:
            return
        umap = self._user_map()
        if idx == 0:
            others = [u for u in self._all_users() if u["id"] != self.uid]
            target = self._pick_user(others, "Follow User")
            if target:
                if self.follows_svc.follow(self.uid, target["id"]):
                    log.info("%s followed %s", self._user["email"], target["email"])
                    print(f"\n  You are now following {_user_label(target)}.")
                else:
                    print("\n  Already following that user.")
        elif idx == 1:
            followee_ids = self.follows_svc._followers.followees_of(self.uid)
            followees = [u for u in umap.values() if u["id"] in followee_ids]
            target = self._pick_user(followees, "Unfollow User")
            if target:
                if self.follows_svc.unfollow(self.uid, target["id"]):
                    log.info("%s unfollowed %s", self._user["email"], target["email"])
                    print(f"\n  You unfollowed {_user_label(target)}.")
                else:
                    print("\n  You weren't following that user.")
        elif idx == 2:
            _title("Who I Follow")
            ids = self.follows_svc._followers.followees_of(self.uid)
            if not ids:
                print("  You aren't following anyone yet.")
            else:
                for uid in ids:
                    u = umap.get(uid)
                    if u:
                        print(f"  • {_user_label(u)}")
        elif idx == 3:
            _title("My Followers")
            ids = self.follows_svc._followers.followers_of(self.uid)
            if not ids:
                print("  No followers yet.")
            else:
                for uid in ids:
                    u = umap.get(uid)
                    if u:
                        print(f"  • {_user_label(u)}")
        _pause()

    # ====================================================================
    # TIMELINE
    # ====================================================================

    def _timeline_menu(self) -> None:
        if not _require_user(self):
            return
        _title("Timeline")
        try:
            raw = input("  Limit (default 20): ").strip()
            limit = max(1, int(raw)) if raw else 20
        except ValueError:
            limit = 20

        feed = self.posts_svc.timeline_for(self.uid, limit)
        if not feed:
            print("  No posts in your timeline. Follow some users!")
        else:
            umap = self._user_map()
            meta = self._enrich_metadata(feed)
            for p in feed:
                print(f"\n  {'─' * (WIDTH - 6)}")
                print(f"  {_post_line(p, umap, meta.get(p['id']))}")
        _pause()


def main() -> None:
    try:
        App().run()
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
