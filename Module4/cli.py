"""Professional menu-driven CLI for the social media platform."""

import getpass
import sys
from pathlib import Path
from typing import Any

_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from social_media.composition import build_services  # noqa: E402
from social_media.exceptions import (  # noqa: E402
    InvalidBioError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidFullNameError,
    UserAlreadyExistsError,
    WeakPasswordError,
)
from social_media.utils.logger import get_logger  # noqa: E402

log = get_logger("cli")

WIDTH = 62


def _line(ch="─") -> str:
    """Return a horizontal rule of the standard display width."""
    return ch * WIDTH


def _title(text: str) -> None:
    """Print a centered title wrapped in a double-line banner."""
    pad = (WIDTH - len(text) - 2) // 2
    print(f"\n{'═' * WIDTH}")
    print(f"{' ' * pad}{text}{' ' * (WIDTH - len(text) - 2 - pad)}")
    print(f"{'═' * WIDTH}")


def _menu(title: str, items: list[str]) -> int | None:
    """Print a numbered menu; return the chosen index or None when backing out."""
    print(f"\n  {title}")
    print(f"  {_line('─')}")
    for position, item in enumerate(items, 1):
        print(f"    {position:>2}. {item}")
    print(f"    {'─' * (WIDTH - 4)}")
    while True:
        try:
            choice_text = input(f"\n    Choice (1-{len(items)}, 0=back): ").strip()
            if choice_text == "0":
                return None
            choice = int(choice_text) - 1
            if 0 <= choice < len(items):
                return choice
            print(f"    Invalid choice. Enter 1-{len(items)} or 0.")
        except ValueError:
            print("    Enter a number.")


def _user_label(user: dict) -> str:
    """Format a user doc as 'Name <email>'."""
    name = user.get("full_name") or "???"
    return f"{name} <{user['email']}>"


def _metadata_line(metadata: dict | None) -> str:
    """Render a metadata doc's tags/location as one display string."""
    if metadata is None:
        return ""
    parts = []
    if metadata.get("tags"):
        parts.append(f"🏷 {' '.join(f'#{tag}' for tag in metadata['tags'])}")
    if metadata.get("location"):
        parts.append(f"📍 {metadata['location']}")
    return " | ".join(parts) if parts else ""


def _post_line(post: dict, user_map: dict, metadata: dict | None = None) -> str:
    """Render a post with author label, counts, and optional metadata."""
    author = user_map.get(post["user_id"], {})
    label = _user_label(author) if author else str(post["user_id"])
    metadata_str = _metadata_line(metadata)
    lines = [
        f"    [{post['id']}] {post['content']}",
        f"    {label}  ♥ {post.get('like_count', 0)}  💬 {post.get('comment_count', 0)}",
    ]
    if metadata_str:
        lines.insert(1, f"    {metadata_str}")
    return "\n".join(lines)


def _pause() -> None:
    """Block until the user presses Enter."""
    input(f"\n    {'─' * (WIDTH - 4)}\n    Press Enter to continue...")


def _prompt_password(prompt: str) -> str:
    """Read a password without echoing it to the terminal."""
    return getpass.getpass(prompt).strip()


def _require_user(app: "App") -> bool:
    """Guard for logged-in actions; returns False (after a message) if logged out."""
    if not app.user:
        print("\n    You must be logged in to do that.")
        _pause()
        return False
    return True


class App:
    """Application shell — wires services and runs the menu loop."""

    def __init__(self) -> None:
        services = build_services()
        self.users_svc = services["users"]
        self.posts_svc = services["posts"]
        self.likes_svc = services["likes"]
        self.comments_svc = services["comments"]
        self.follows_svc = services["follows"]
        self._metadata_repo = services["metadata_repo"]
        self._user: dict | None = None

    # -- properties -------------------------------------------------------

    @property
    def user(self) -> dict | None:
        """The currently logged-in user doc, or None."""
        return self._user

    @property
    def user_id(self) -> Any:
        """ID of the logged-in user, or None."""
        return self._user["id"] if self._user else None

    # -- user helpers -----------------------------------------------------

    def _all_users(self) -> list[dict]:
        """Return every user doc stored in the repository."""
        return list(self.users_svc._user_repo.find({}))

    def _user_map(self) -> dict:
        """Return a {user_id: user_doc} lookup table for all users."""
        return {user["id"]: user for user in self._all_users()}

    def _pick_user(self, users: list[dict], title: str) -> dict | None:
        """Show a numbered picker and return the chosen user, or None on back."""
        if not users:
            print("\n  No users found.")
            return None
        print(f"\n  {title}")
        print(f"  {_line('─')}")
        for position, user in enumerate(users, 1):
            print(f"    {position:>2}. {_user_label(user)}")
        print(f"    {'─' * (WIDTH - 4)}")
        while True:
            try:
                choice_text = input(f"\n    Pick a user (1-{len(users)}, 0=back): ").strip()
                if choice_text == "0":
                    return None
                choice = int(choice_text) - 1
                if 0 <= choice < len(users):
                    return users[choice]
                print(f"    Invalid choice. Enter 1-{len(users)} or 0.")
            except ValueError:
                print("    Enter a number.")

    # -- post helpers -----------------------------------------------------

    def _enrich_metadata(self, posts: list[dict]) -> dict[Any, dict]:
        """Fetch metadata docs for the given posts, keyed by post id."""
        post_ids = [post["id"] for post in posts]
        return self._metadata_repo.find_many(post_ids)

    def _all_posts(self) -> tuple[list[dict], dict, dict[Any, dict]]:
        """Return (posts, user_map, metadata) for every post in the system."""
        posts = list(self.posts_svc._post_repo.find({}))
        user_map = self._user_map()
        metadata = self._enrich_metadata(posts)
        return posts, user_map, metadata

    def _my_posts(self) -> tuple[list[dict], dict, dict[Any, dict]]:
        """Return (posts, user_map, metadata) for the logged-in user's posts."""
        posts = list(self.posts_svc._post_repo.find({"user_id": self.user_id}))
        user_map = self._user_map()
        metadata = self._enrich_metadata(posts)
        return posts, user_map, metadata

    def _pick_post(
        self,
        posts: list[dict],
        user_map: dict,
        title: str,
        metadata: dict[Any, dict] | None = None,
    ) -> dict | None:
        """Show a numbered post picker; return the chosen post, or None on back."""
        if not posts:
            print("\n  No posts found.")
            return None
        metadata = metadata or {}
        print(f"\n  {title}")
        print(f"  {_line('─')}")
        for position, post in enumerate(posts, 1):
            author = user_map.get(post["user_id"], {})
            label = _user_label(author) if author else post["user_id"]
            metadata_str = _metadata_line(metadata.get(post["id"]))
            print(f"    {position:>2}. {post['content'][:50]}")
            if metadata_str:
                print(f"       {metadata_str}")
            print(
                f"       {label}  ♥ {post.get('like_count', 0)}  💬 {post.get('comment_count', 0)}"
            )
        print(f"    {'─' * (WIDTH - 4)}")
        while True:
            try:
                choice_text = input(f"\n    Pick a post (1-{len(posts)}, 0=back): ").strip()
                if choice_text == "0":
                    return None
                choice = int(choice_text) - 1
                if 0 <= choice < len(posts):
                    return posts[choice]
                print(f"    Invalid choice. Enter 1-{len(posts)} or 0.")
            except ValueError:
                print("    Enter a number.")

    def _post_action_menu(
        self, post: dict, user_map: dict, metadata: dict[Any, dict] | None = None
    ) -> None:
        """Loop over like/unlike/comment/view/edit/delete actions for one post."""
        assert self._user is not None
        metadata = metadata or {}
        is_owner = post["user_id"] == self.user_id
        while True:
            _title("Post Actions")
            author = user_map.get(post["user_id"], {})
            label = _user_label(author) if author else post["user_id"]
            print(f"  {post['content']}")
            metadata_str = _metadata_line(metadata.get(post["id"]))
            if metadata_str:
                print(f"  {metadata_str}")
            print(f"  {label}  ♥ {post.get('like_count', 0)}  💬 {post.get('comment_count', 0)}")
            items = ["Like", "Unlike", "Comment", "View Comments"]
            if is_owner:
                items.extend(["Edit", "Delete"])
            choice = _menu("Post Actions", items)
            if choice is None:
                return
            if choice == 0:
                _title("Like Post")
                if self.likes_svc.like(self.user_id, post["id"]):
                    log.info("Post liked by %s", self._user["email"])
                    print("  You liked the post.")
                    post["like_count"] = post.get("like_count", 0) + 1
                else:
                    print("  You already liked that post.")
            elif choice == 1:
                _title("Unlike Post")
                if self.likes_svc.unlike(self.user_id, post["id"]):
                    log.info("Post unliked by %s", self._user["email"])
                    print("  You unliked the post.")
                    post["like_count"] = max(0, post.get("like_count", 0) - 1)
                else:
                    print("  You hadn't liked that post.")
            elif choice == 2:
                _title("Comment")
                content = input("  Comment: ").strip()
                if content:
                    comment = self.comments_svc.add(post["id"], self.user_id, content)
                    log.info("Comment added by %s", self._user["email"])
                    print(f"\n  Comment added! ID: {comment['id']}")
                    post["comment_count"] = post.get("comment_count", 0) + 1
                else:
                    print("\n  Comment cannot be empty.")
            elif choice == 3:
                _title("Comments")
                comments = self.comments_svc.for_post(post["id"])
                if not comments:
                    print("  No comments yet.")
                else:
                    for comment in comments:
                        author = user_map.get(comment["user_id"], {})
                        label = _user_label(author) if author else comment["user_id"]
                        print(f"\n  [{comment['id']}] {label}")
                        print(f"  {comment['content']}")
            elif choice == 4 and is_owner:
                _title("Edit Post")
                new_content = input("  New content: ").strip()
                if new_content:
                    print("  Metadata (optional, press Enter to skip):")
                    tags_raw = input("    Tags (comma-separated): ").strip()
                    tags = (
                        [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
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
            elif choice == 5 and is_owner:
                self.posts_svc.soft_delete(post["id"])
                log.info("Post deleted by %s", self._user["email"])
                print("  Post deleted.")
                return
            _pause()

    # ====================================================================
    # MAIN LOOP
    # ====================================================================

    def run(self) -> None:
        """Run the main menu loop until the user quits."""
        while True:
            self._main_menu()

    def _main_menu(self) -> None:
        """Render the top-level menu and dispatch to the chosen section."""
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
                "Profile",
                "Posts",
                "Follows",
                "Timeline",
                "Logout",
            ]
            choice = _menu("Main Menu", items)
            if choice is None:
                return
            {
                0: self._profile_menu,
                1: self._posts_menu,
                2: self._follows_menu,
                3: self._timeline_menu,
                4: self._logout,
            }[choice]()
        else:
            items = ["Login", "Register"]
            choice = _menu("Main Menu", items)
            if choice is None:
                return
            if choice == 0:
                self._login()
            else:
                self._register()

    # ====================================================================
    # AUTH
    # ====================================================================

    def _login(self) -> None:
        """Authenticate an existing user and store the session."""
        _title("Login")
        email = input("  Email    : ").strip()
        password = _prompt_password("  Password : ")
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
        """Create a new user account."""
        _title("Register")
        email = input("  Email     : ").strip()
        password = _prompt_password("  Password  : ")
        name = input("  Full name : ").strip() or None
        bio = input("  Bio       : ").strip() or None
        try:
            user = self.users_svc.register(email, password, name, bio)
            log.info("User registered: %s", email)
            print(f"\n  Registered {_user_label(user)}.")
        except UserAlreadyExistsError:
            log.warning("Registration failed (exists): %s", email)
            print(f"\n  User already exists: {email}")
        except InvalidEmailError as error:
            log.warning("Registration failed (invalid email): %s", email)
            print(f"\n  {error}")
        except WeakPasswordError as error:
            log.warning("Registration failed (weak password): %s", email)
            print(f"\n  {error}")
        except InvalidFullNameError as error:
            log.warning("Registration failed (invalid full name): %s", email)
            print(f"\n  {error}")
        except InvalidBioError as error:
            log.warning("Registration failed (invalid bio): %s", email)
            print(f"\n  {error}")
        _pause()

    def _logout(self) -> None:
        """End the current user session."""
        log.info("User logged out: %s", self._user["email"] if self._user else "?")
        self._user = None
        print("\n  Logged out.")
        _pause()

    # ====================================================================
    # PROFILE
    # ====================================================================

    def _profile_menu(self) -> None:
        """Profile sub-menu: view and update my own profile details."""
        if not _require_user(self):
            return
        assert self._user is not None
        while True:
            _title("My Profile")
            user = self._user
            print(f"  Name      : {user.get('full_name') or '—'}")
            print(f"  Email     : {user['email']}")
            print(f"  Bio       : {user.get('bio') or '—'}")
            print(f"  User ID   : {user['id']}")
            print(f"  Active    : {user.get('is_active', True)}")
            choice = _menu("Profile Actions", ["Edit Profile"])
            if choice is None:
                return
            self._edit_profile()

    def _edit_profile(self) -> None:
        """Update profile details; empty input keeps the current value."""
        assert self._user is not None
        _title("Edit Profile")
        print("  (Press Enter to keep the current value)")
        current_name = self._user.get("full_name") or ""
        current_bio = self._user.get("bio") or ""
        name = input(f"  Full name [{current_name}]: ").strip() or current_name
        bio = input(f"  Bio [{current_bio}]: ").strip() or current_bio
        email = input(f"  Email [{self._user['email']}]: ").strip() or self._user["email"]
        try:
            self._user = self.users_svc.update_profile(
                self.user_id, full_name=name, bio=bio, email=email
            )
            assert self._user is not None
            log.info("Profile updated: %s", self._user["email"])
            print("\n  Profile updated.")
        except InvalidEmailError as error:
            print(f"\n  {error}")
        except InvalidFullNameError as error:
            print(f"\n  {error}")
        except InvalidBioError as error:
            print(f"\n  {error}")
        except UserAlreadyExistsError as error:
            print(f"\n  {error}")
        _pause()

    # ====================================================================
    # POSTS
    # ====================================================================

    def _posts_menu(self) -> None:
        """Posts sub-menu: create, browse all, my posts, and trending."""
        if not _require_user(self):
            return
        items = ["Create Post", "Browse All Posts", "My Posts", "Trending Posts"]
        choice = _menu("Posts", items)
        if choice is None:
            return
        if choice == 0:
            _title("Create Post")
            content = input("  Content: ").strip()
            if content:
                print("  Metadata (optional, press Enter to skip):")
                tags_raw = input("    Tags (comma-separated): ").strip()
                tags = (
                    [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
                    if tags_raw
                    else None
                )
                location = input("    Location: ").strip() or None
                post = self.posts_svc.create(self.user_id, content, tags=tags, location=location)
                snippet = f'"{content[:40]}{"..." if len(content) > 40 else ""}"'
                assert self._user is not None
                log.info("Post created by %s: %s", self._user["email"], snippet)
                print(f"\n  Posted! ID: {post['id']}")
            else:
                print("\n  Content cannot be empty.")
        elif choice == 1:
            posts, user_map, metadata = self._all_posts()
            post = self._pick_post(posts, user_map, "All Posts", metadata)
            if post:
                self._post_action_menu(post, user_map, metadata)
        elif choice == 2:
            posts, user_map, metadata = self._my_posts()
            post = self._pick_post(posts, user_map, "My Posts", metadata)
            if post:
                self._post_action_menu(post, user_map, metadata)
        elif choice == 3:
            _title("Trending Posts")
            user_map = self._user_map()
            trending = self.posts_svc.trending()
            if not trending:
                print("  Nothing trending yet.")
            else:
                for rank, post in enumerate(trending, 1):
                    author = user_map.get(post["user_id"], {})
                    label = _user_label(author) if author else post["user_id"]
                    print(f"\n  {rank:>2}. {post['content'][:50]}")
                    print(f"      {label}  ♥ {post['like_count']}  💬 {post['comment_count']}")
        _pause()

    # ====================================================================
    # FOLLOWS
    # ====================================================================

    def _follows_menu(self) -> None:
        """Follows sub-menu: follow, unfollow, and list following/followers."""
        if not _require_user(self):
            return
        assert self._user is not None
        items = ["Follow a User", "Unfollow a User", "Who I Follow", "My Followers"]
        choice = _menu("Follows", items)
        if choice is None:
            return
        user_map = self._user_map()
        if choice == 0:
            others = [user for user in self._all_users() if user["id"] != self.user_id]
            target = self._pick_user(others, "Follow User")
            if target:
                if self.follows_svc.follow(self.user_id, target["id"]):
                    log.info("%s followed %s", self._user["email"], target["email"])
                    print(f"\n  You are now following {_user_label(target)}.")
                else:
                    print("\n  Already following that user.")
        elif choice == 1:
            followee_ids = self.follows_svc._follower_repo.followees_of(self.user_id)
            followees = [user for user in user_map.values() if user["id"] in followee_ids]
            target = self._pick_user(followees, "Unfollow User")
            if target:
                if self.follows_svc.unfollow(self.user_id, target["id"]):
                    log.info("%s unfollowed %s", self._user["email"], target["email"])
                    print(f"\n  You unfollowed {_user_label(target)}.")
                else:
                    print("\n  You weren't following that user.")
        elif choice == 2:
            _title("Who I Follow")
            followee_ids = self.follows_svc._follower_repo.followees_of(self.user_id)
            if not followee_ids:
                print("  You aren't following anyone yet.")
            else:
                for user_id in followee_ids:
                    user = user_map.get(user_id)
                    if user:
                        print(f"  • {_user_label(user)}")
        elif choice == 3:
            _title("My Followers")
            follower_ids = self.follows_svc._follower_repo.followers_of(self.user_id)
            if not follower_ids:
                print("  No followers yet.")
            else:
                for user_id in follower_ids:
                    user = user_map.get(user_id)
                    if user:
                        print(f"  • {_user_label(user)}")
        _pause()

    # ====================================================================
    # TIMELINE
    # ====================================================================

    def _timeline_menu(self) -> None:
        """Show the logged-in user's cached timeline feed."""
        if not _require_user(self):
            return
        _title("Timeline")
        try:
            raw_limit = input("  Limit (default 20): ").strip()
            limit = max(1, int(raw_limit)) if raw_limit else 20
        except ValueError:
            limit = 20

        feed = self.posts_svc.timeline_for(self.user_id, limit)
        if not feed:
            print("  No posts in your timeline. Follow some users!")
        else:
            user_map = self._user_map()
            metadata = self._enrich_metadata(feed)
            for post in feed:
                print(f"\n  {'─' * (WIDTH - 6)}")
                print(f"  {_post_line(post, user_map, metadata.get(post['id']))}")
        _pause()


def main() -> None:
    """Entry point — boot the app and exit cleanly on Ctrl+C."""
    try:
        App().run()
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
