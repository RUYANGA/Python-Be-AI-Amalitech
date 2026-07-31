"""Tests for the CLI application menus and helpers."""

import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import cli
import pytest
from cli import App, _menu, _metadata_line, _post_line, _user_label

from tests.conftest import fake_id, mock_cli_services, post_doc, user_doc


class TestHelpers:
    def test_user_label_with_name(self):
        doc = {"full_name": "Alice", "email": "alice@example.com"}
        assert _user_label(doc) == "Alice <alice@example.com>"

    def test_user_label_without_name(self):
        doc = {"full_name": None, "email": "bob@example.com"}
        assert _user_label(doc) == "??? <bob@example.com>"

    def test_user_label_missing_name_key(self):
        doc = {"email": "bob@example.com"}
        assert _user_label(doc) == "??? <bob@example.com>"

    def test_post_line(self):
        uid = fake_id()
        umap = {uid: user_doc(email="alice@example.com", full_name="Alice")}
        p = post_doc(uid, content="Hello!", like_count=3, comment_count=1)
        result = _post_line(p, umap)
        assert "Hello!" in result
        assert "Alice" in result
        assert "♥ 3" in result
        assert "💬 1" in result

    def test_post_line_unknown_user(self):
        uid = fake_id()
        umap: dict = {}
        p = post_doc(uid, content="Hello!")
        result = _post_line(p, umap)
        assert str(uid) in result


class TestAppInit:
    def test_app_creates_services(self):
        with patch("cli.build_services") as mock_build:
            mock_build.return_value = mock_cli_services()
            app = App()
            assert app._user is None
            mock_build.assert_called_once()


class TestAuthFlow:
    def test_login_success(self):
        with patch("cli.build_services") as mock_build:
            svc = mock_cli_services()
            svc["users"].authenticate.return_value = user_doc(email="a@b.com")
            mock_build.return_value = svc

            app = App()
            with patch("builtins.input", side_effect=["a@b.com", "pw", ""]):
                app._login()
            assert app._user is not None
            assert app._user["email"] == "a@b.com"

    def test_login_failure(self):
        with patch("cli.build_services") as mock_build:
            svc = mock_cli_services()
            from social_media.exceptions import InvalidCredentialsError

            svc["users"].authenticate.side_effect = InvalidCredentialsError()
            mock_build.return_value = svc

            app = App()
            with patch("builtins.input", side_effect=["a@b.com", "wrong", ""]):
                app._login()
            assert app._user is None

    def test_register_success(self):
        with patch("cli.build_services") as mock_build:
            svc = mock_cli_services()
            svc["users"].register.return_value = user_doc(email="new@b.com", full_name="New")
            mock_build.return_value = svc

            app = App()
            with patch("builtins.input", side_effect=["new@b.com", "pw", "New", ""]):
                app._register()
            svc["users"].register.assert_called_once_with("new@b.com", "pw", "New")

    def test_register_duplicate(self):
        with patch("cli.build_services") as mock_build:
            svc = mock_cli_services()
            from social_media.exceptions import UserAlreadyExistsError

            svc["users"].register.side_effect = UserAlreadyExistsError("dup@b.com")
            mock_build.return_value = svc

            app = App()
            with patch("builtins.input", side_effect=["dup@b.com", "pw", "", ""]):
                app._register()

    def test_logout(self):
        with patch("cli.build_services") as mock_build:
            mock_build.return_value = mock_cli_services()
            app = App()
            app._user = user_doc()
            with patch("builtins.input", return_value=""):
                app._logout()
            assert app._user is None


class TestProfileMenu:
    def test_my_profile(self):
        with patch("cli.build_services") as mock_build:
            mock_build.return_value = mock_cli_services()
            app = App()
            app._user = user_doc(full_name="Alice", email="alice@b.com")
            with patch("builtins.input", side_effect=["1", ""]):
                app._profile_menu()

    def test_list_all_users(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["users"]._users.find.return_value = [
                user_doc(email="a@b.com", full_name="A"),
                user_doc(email="b@b.com", full_name="B"),
            ]
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["2", ""]):
                app._profile_menu()


class TestPostsMenu:
    def test_create_post(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"].create.return_value = {"id": fake_id(), "content": "Test"}
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["1", "Test post content", "", "", ""]):
                app._posts_menu()
            svcs["posts"].create.assert_called_once()

    def test_browse_all_posts_empty(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"]._posts.find.return_value = []
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["2", ""]):
                app._posts_menu()

    def test_browse_all_posts_pick_one(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            uid = fake_id()
            p = post_doc(uid, content="First post")
            svcs["posts"]._posts.find.return_value = [p]
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["2", "1", "0", ""]):
                app._posts_menu()

    def test_my_posts_empty(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"]._posts.find.return_value = []
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["3", ""]):
                app._posts_menu()


class TestFollowsMenu:
    def test_follow_user(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            me = user_doc(email="me@b.com")
            target = user_doc(email="bob@b.com")
            svcs["users"]._users.find.return_value = [me, target]
            svcs["follows"].follow.return_value = True
            mock_build.return_value = svcs

            app = App()
            app._user = me
            with patch("builtins.input", side_effect=["1", "1", ""]):
                app._follows_menu()
            svcs["follows"].follow.assert_called_once()

    def test_follow_already_following(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            me = user_doc(email="me@b.com")
            target = user_doc(email="bob@b.com")
            svcs["users"]._users.find.return_value = [me, target]
            svcs["follows"].follow.return_value = False
            mock_build.return_value = svcs

            app = App()
            app._user = me
            with patch("builtins.input", side_effect=["1", "1", ""]):
                app._follows_menu()


class TestPostActions:
    def test_like_post(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["likes"].like.return_value = True
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            post = post_doc(fake_id(), content="Test")
            umap = {post["user_id"]: user_doc()}
            with patch("builtins.input", side_effect=["1", "", "0"]):
                app._post_action_menu(post, umap)
            svcs["likes"].like.assert_called_once_with(app.uid, post["id"])

    def test_comment_on_post(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["comments"].add.return_value = {"id": fake_id(), "content": "Nice!"}
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            post = post_doc(fake_id(), content="Test")
            umap = {post["user_id"]: user_doc()}
            with patch("builtins.input", side_effect=["3", "Great post!", "", "0"]):
                app._post_action_menu(post, umap)
            svcs["comments"].add.assert_called_once()

    def test_view_comments(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["comments"].for_post.return_value = []
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            post = post_doc(fake_id(), content="Test")
            umap = {post["user_id"]: user_doc()}
            with patch("builtins.input", side_effect=["4", "", "0"]):
                app._post_action_menu(post, umap)

    def test_edit_own_post(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"].update.return_value = {
                "id": fake_id(),
                "user_id": user_doc()["id"],
                "content": "Edited content",
            }
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            post = post_doc(app.uid, content="My post")
            umap = {app.uid: app._user}
            with patch("builtins.input", side_effect=["5", "Edited content", "", "", "", "0"]):
                app._post_action_menu(post, umap)
            svcs["posts"].update.assert_called_once()

    def test_delete_own_post(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            post = post_doc(app.uid, content="My post")
            umap = {app.uid: app._user}
            with patch("builtins.input", side_effect=["6", ""]):
                app._post_action_menu(post, umap)
            svcs["posts"].soft_delete.assert_called_once_with(post["id"])


class TestTimelineMenu:
    def test_timeline_with_posts(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"].timeline_for.return_value = [
                post_doc(fake_id(), content="Post 1"),
                post_doc(fake_id(), content="Post 2"),
            ]
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["", ""]):
                app._timeline_menu()

    def test_timeline_empty(self):
        with patch("cli.build_services") as mock_build:
            svcs = mock_cli_services()
            svcs["posts"].timeline_for.return_value = []
            mock_build.return_value = svcs

            app = App()
            app._user = user_doc()
            with patch("builtins.input", side_effect=["10", ""]):
                app._timeline_menu()


@pytest.fixture
def app_factory():
    """Build an App from mocked services with an optional logged-in user."""

    def factory(user=None, **svc_overrides):
        svcs = mock_cli_services(**svc_overrides)
        with patch("cli.build_services", return_value=svcs):
            app = App()
        if user is not None:
            app._user = user
        return app, svcs

    return factory


class TestMenuHelpers:
    def test_menu_invalid_choice_then_valid(self):
        with patch("builtins.input", side_effect=["9", "1"]):
            assert _menu("T", ["A", "B"]) == 0

    def test_menu_value_error_then_valid(self):
        with patch("builtins.input", side_effect=["x", "1"]):
            assert _menu("T", ["A", "B"]) == 0

    def test_menu_back_returns_none(self):
        with patch("builtins.input", side_effect=["0"]):
            assert _menu("T", ["A"]) is None


class TestMetadataHelpers:
    def test_metadata_line_tags_and_location(self):
        result = _metadata_line({"tags": ["py", "ai"], "location": "Accra"})
        assert "#py" in result and "#ai" in result
        assert "Accra" in result

    def test_metadata_line_location_only(self):
        assert "Kumasi" in _metadata_line({"location": "Kumasi"})

    def test_metadata_line_no_parts(self):
        assert _metadata_line({"other": 1}) == ""

    def test_post_line_with_metadata(self):
        uid = fake_id()
        umap = {uid: user_doc(full_name="Alice")}
        p = post_doc(uid, content="Hello", like_count=2, comment_count=1)
        result = _post_line(p, umap, {"tags": ["x"]})
        assert "#x" in result


class TestRequireUser:
    def test_require_user_false_when_logged_out(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            assert cli._require_user(app) is False

    def test_require_user_true_when_logged_in(self, app_factory):
        app, _ = app_factory(user=user_doc())
        assert cli._require_user(app) is True


class TestUserPickers:
    def test_find_user_by_email(self, app_factory):
        app, svcs = app_factory()
        svcs["users"]._users.find_by_email.return_value = {
            "id": fake_id(),
            "email": "a@b.com",
        }
        assert app._find_user_by_email("a@b.com")["email"] == "a@b.com"

    def test_pick_user_empty(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            assert app._pick_user([], "Pick") is None

    def test_pick_user_back(self, app_factory):
        app, _ = app_factory()
        users = [user_doc(), user_doc()]
        with patch("builtins.input", side_effect=["0"]):
            assert app._pick_user(users, "Pick") is None

    def test_pick_user_invalid_then_valid(self, app_factory):
        app, _ = app_factory()
        users = [user_doc(), user_doc()]
        with patch("builtins.input", side_effect=["9", "1"]):
            picked = app._pick_user(users, "Pick")
        assert picked["id"] == users[0]["id"]

    def test_pick_user_value_error(self, app_factory):
        app, _ = app_factory()
        users = [user_doc(), user_doc()]
        with patch("builtins.input", side_effect=["abc", "2"]):
            picked = app._pick_user(users, "Pick")
        assert picked["id"] == users[1]["id"]


class TestMainMenu:
    def test_logged_out_back(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", side_effect=["0"]):
            app._main_menu()

    def test_logged_out_login(self, app_factory):
        app, svcs = app_factory()
        svcs["users"].authenticate.return_value = user_doc(email="a@b.com")
        with patch("builtins.input", side_effect=["1", "a@b.com", "pw", ""]):
            app._main_menu()
        assert app._user is not None

    def test_logged_out_register(self, app_factory):
        app, svcs = app_factory()
        svcs["users"].register.return_value = user_doc(email="new@b.com")
        with patch("builtins.input", side_effect=["2", "new@b.com", "pw", "New", ""]):
            app._main_menu()

    def test_logged_in_back(self, app_factory):
        app, _ = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["0"]):
            app._main_menu()

    def test_logged_in_dispatch_to_logout(self, app_factory):
        app, _ = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["5", ""]):
            app._main_menu()
        assert app._user is None


class TestRegisterErrors:
    def test_register_invalid_email(self, app_factory):
        app, svcs = app_factory()
        from social_media.exceptions import InvalidEmailError

        svcs["users"].register.side_effect = InvalidEmailError("bad email")
        with patch("builtins.input", side_effect=["bad", "pw", "New", ""]):
            app._register()

    def test_register_weak_password(self, app_factory):
        app, svcs = app_factory()
        from social_media.exceptions import WeakPasswordError

        svcs["users"].register.side_effect = WeakPasswordError("too weak")
        with patch("builtins.input", side_effect=["e@b.com", "pw", "New", ""]):
            app._register()


class TestProfileMenuExtra:
    def test_not_logged_in(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            app._profile_menu()

    def test_back(self, app_factory):
        app, _ = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["0"]):
            app._profile_menu()

    def test_search_user_found(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["users"]._users.find_by_email.return_value = user_doc(email="a@b.com")
        with patch("builtins.input", side_effect=["3", "a@b.com", ""]):
            app._profile_menu()

    def test_search_user_not_found(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["users"]._users.find_by_email.return_value = None
        with patch("builtins.input", side_effect=["3", "nope@b.com", ""]):
            app._profile_menu()


class TestPostsMenuExtra:
    def test_not_logged_in(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            app._posts_menu()

    def test_back(self, app_factory):
        app, _ = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["0"]):
            app._posts_menu()

    def test_create_post_empty_content(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["1", "", ""]):
            app._posts_menu()
        svcs["posts"].create.assert_not_called()

    def test_my_posts_pick_one(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        p = post_doc(app.uid, content="Mine")
        svcs["posts"]._posts.find.return_value = [p]
        with patch("builtins.input", side_effect=["3", "1", "0", ""]):
            app._posts_menu()

    def test_trending_empty(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"].trending.return_value = []
        with patch("builtins.input", side_effect=["4", ""]):
            app._posts_menu()

    def test_trending_with_posts(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        author = user_doc(full_name="Alice")
        hot = {
            "id": fake_id(),
            "user_id": author["id"],
            "content": "Hot",
            "score": 3,
            "like_count": 2,
            "comment_count": 1,
        }
        svcs["posts"].trending.return_value = [hot]
        svcs["users"]._users.find.return_value = [author]
        with patch("builtins.input", side_effect=["4", ""]):
            app._posts_menu()


class TestPostPickExtra:
    def test_pick_post_back(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"]._posts.find.return_value = [post_doc(fake_id(), content="Hi")]
        with patch("builtins.input", side_effect=["2", "0", ""]):
            app._posts_menu()

    def test_pick_post_invalid_then_valid(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"]._posts.find.return_value = [post_doc(fake_id(), content="Hi")]
        with patch("builtins.input", side_effect=["2", "99", "1", "0", ""]):
            app._posts_menu()

    def test_pick_post_value_error(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"]._posts.find.return_value = [post_doc(fake_id(), content="Hi")]
        with patch("builtins.input", side_effect=["2", "abc", "1", "0", ""]):
            app._posts_menu()

    def test_pick_post_with_metadata(self, app_factory):
        from tests.conftest import make_metadata_repo

        p = post_doc(fake_id(), content="Hi")
        md_repo = make_metadata_repo()
        md_repo.find_many.return_value = {p["id"]: {"tags": ["x"]}}
        app, svcs = app_factory(user=user_doc(), metadata_repo=md_repo)
        svcs["posts"]._posts.find.return_value = [p]
        with patch("builtins.input", side_effect=["2", "1", "0", ""]):
            app._posts_menu()


class TestPostActionsExtra:
    def test_shows_metadata(self, app_factory):
        app, _ = app_factory(user=user_doc())
        post = post_doc(app.uid, content="My post")
        umap = {app.uid: app._user}
        md = {post["id"]: {"tags": ["x"], "location": "Accra"}}
        with patch("builtins.input", side_effect=["0"]):
            app._post_action_menu(post, umap, md)

    def test_like_already_liked(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["likes"].like.return_value = False
        post = post_doc(fake_id(), content="Test")
        umap = {post["user_id"]: user_doc()}
        with patch("builtins.input", side_effect=["1", "", "0"]):
            app._post_action_menu(post, umap)

    def test_unlike_post(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["likes"].unlike.return_value = True
        post = post_doc(fake_id(), content="Test")
        umap = {post["user_id"]: user_doc()}
        with patch("builtins.input", side_effect=["2", "", "0"]):
            app._post_action_menu(post, umap)

    def test_unlike_not_liked(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["likes"].unlike.return_value = False
        post = post_doc(fake_id(), content="Test")
        umap = {post["user_id"]: user_doc()}
        with patch("builtins.input", side_effect=["2", "", "0"]):
            app._post_action_menu(post, umap)

    def test_comment_empty(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        post = post_doc(fake_id(), content="Test")
        umap = {post["user_id"]: user_doc()}
        with patch("builtins.input", side_effect=["3", "", "", "0"]):
            app._post_action_menu(post, umap)
        svcs["comments"].add.assert_not_called()

    def test_view_comments_with_items(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        author = user_doc(full_name="Alice")
        svcs["comments"].for_post.return_value = [
            {"id": fake_id(), "user_id": author["id"], "content": "Hi"}
        ]
        post = post_doc(fake_id(), content="Test")
        umap = {author["id"]: author}
        with patch("builtins.input", side_effect=["4", "", "0"]):
            app._post_action_menu(post, umap)

    def test_edit_post_not_found(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"].update.return_value = None
        post = post_doc(app.uid, content="My post")
        umap = {app.uid: app._user}
        with patch("builtins.input", side_effect=["5", "New", "t1,t2", "Accra", "", "0"]):
            app._post_action_menu(post, umap)

    def test_edit_post_empty_content(self, app_factory):
        app, _ = app_factory(user=user_doc())
        post = post_doc(app.uid, content="My post")
        umap = {app.uid: app._user}
        with patch("builtins.input", side_effect=["5", "", "", "0"]):
            app._post_action_menu(post, umap)


class TestFollowsMenuExtra:
    def test_not_logged_in(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            app._follows_menu()

    def test_back(self, app_factory):
        app, _ = app_factory(user=user_doc())
        with patch("builtins.input", side_effect=["0"]):
            app._follows_menu()

    def _with_target(self, app_factory):
        me = user_doc(email="me@b.com")
        target = user_doc(email="bob@b.com")
        app, svcs = app_factory(user=me)
        svcs["users"]._users.find.return_value = [me, target]
        return app, svcs, me, target

    def test_unfollow_user(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followees_of.return_value = [target["id"]]
        svcs["follows"].unfollow.return_value = True
        with patch("builtins.input", side_effect=["2", "1", ""]):
            app._follows_menu()

    def test_unfollow_not_following(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followees_of.return_value = [target["id"]]
        svcs["follows"].unfollow.return_value = False
        with patch("builtins.input", side_effect=["2", "1", ""]):
            app._follows_menu()

    def test_who_i_follow_empty(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followees_of.return_value = []
        with patch("builtins.input", side_effect=["3", ""]):
            app._follows_menu()

    def test_who_i_follow_with_users(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followees_of.return_value = [target["id"]]
        with patch("builtins.input", side_effect=["3", ""]):
            app._follows_menu()

    def test_my_followers_empty(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followers_of.return_value = []
        with patch("builtins.input", side_effect=["4", ""]):
            app._follows_menu()

    def test_my_followers_with_users(self, app_factory):
        app, svcs, me, target = self._with_target(app_factory)
        svcs["follows"]._followers.followers_of.return_value = [target["id"]]
        with patch("builtins.input", side_effect=["4", ""]):
            app._follows_menu()


class TestTimelineMenuExtra:
    def test_not_logged_in(self, app_factory):
        app, _ = app_factory()
        with patch("builtins.input", return_value=""):
            app._timeline_menu()

    def test_limit_value_error(self, app_factory):
        app, svcs = app_factory(user=user_doc())
        svcs["posts"].timeline_for.return_value = []
        with patch("builtins.input", side_effect=["abc", ""]):
            app._timeline_menu()


class TestRunAndMain:
    def test_run_loops_until_keyboard_interrupt(self, app_factory):
        app, _ = app_factory()
        with (
            patch("cli.App._main_menu", side_effect=[None, KeyboardInterrupt]),
            pytest.raises(KeyboardInterrupt),
        ):
            app.run()

    def test_main_handles_keyboard_interrupt(self):
        svcs = mock_cli_services()
        with (
            patch("cli.build_services", return_value=svcs),
            patch("cli.App.run", side_effect=KeyboardInterrupt),
            pytest.raises(SystemExit) as exc,
        ):
            cli.main()
        assert exc.value.code == 0

    def test_script_entrypoint_bootstrap_and_main(self):
        src = str(Path(cli.__file__).resolve().parent / "src")
        orig = list(sys.path)
        sys.path[:] = [p for p in orig if p != src]
        try:
            with (
                patch(
                    "social_media.composition.build_services",
                    side_effect=KeyboardInterrupt,
                ),
                pytest.raises(SystemExit) as exc,
            ):
                runpy.run_path(cli.__file__, run_name="__main__")
        finally:
            sys.path[:] = orig
        assert exc.value.code == 0
