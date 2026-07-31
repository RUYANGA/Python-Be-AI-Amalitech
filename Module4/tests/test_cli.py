"""Tests for the CLI application menus and helpers."""

from unittest.mock import patch

from cli import App, _post_line, _user_label

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
            svc["users"].register.return_value = user_doc(
                email="new@b.com", full_name="New"
            )
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
            with patch(
                "builtins.input", side_effect=["1", "Test post content", "", "", ""]
            ):
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
            with patch(
                "builtins.input", side_effect=["5", "Edited content", "", "", "", "0"]
            ):
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
