"""Unit tests for ``ClickEventPublisher``.

``_send`` (the actual REST call) is tested directly and synchronously —
that's where the request-building and failure-swallowing logic lives.
``publish`` is tested separately, only to confirm it hands off to the
background executor rather than blocking the caller.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from apps.shortener.api.services.click_publisher import ClickEventPublisher


class TestSend:
    def test_posts_the_expected_payload(self, settings):
        settings.ANALYTICS_SERVICE_URL = "http://analytics.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        payload = {
            "short_code": "abc1234",
            "ip_address": "1.2.3.4",
            "user_agent": "pytest",
            "referer": "",
        }

        with patch(
            "apps.shortener.api.services.click_publisher.requests.post",
            return_value=mock_response,
        ) as post:
            ClickEventPublisher()._send(payload)

        post.assert_called_once_with(
            "http://analytics.test/api/v1/internal/clicks/",
            json=payload,
            headers={"X-Internal-Token": "shared-secret"},
            timeout=2.0,
        )

    def test_swallows_a_connection_failure(self, settings):
        settings.ANALYTICS_SERVICE_URL = "http://analytics.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with patch(
            "apps.shortener.api.services.click_publisher.requests.post",
            side_effect=requests.ConnectionError("down"),
        ):
            ClickEventPublisher()._send({"short_code": "abc1234"})  # must not raise

    def test_swallows_a_non_2xx_response(self, settings):
        settings.ANALYTICS_SERVICE_URL = "http://analytics.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        with patch(
            "apps.shortener.api.services.click_publisher.requests.post",
            return_value=mock_response,
        ):
            ClickEventPublisher()._send({"short_code": "abc1234"})  # must not raise


class TestPublish:
    def test_dispatches_to_the_background_executor_without_blocking(self):
        publisher = ClickEventPublisher()

        with patch("apps.shortener.api.services.click_publisher._EXECUTOR") as mock_executor:
            publisher.publish(
                "abc1234", ip_address="1.2.3.4", user_agent="pytest", referer="https://ref"
            )

        mock_executor.submit.assert_called_once_with(
            publisher._send,
            {
                "short_code": "abc1234",
                "ip_address": "1.2.3.4",
                "user_agent": "pytest",
                "referer": "https://ref",
            },
        )

    def test_defaults_a_missing_ip_address_to_an_empty_string(self):
        publisher = ClickEventPublisher()

        with patch("apps.shortener.api.services.click_publisher._EXECUTOR") as mock_executor:
            publisher.publish("abc1234")

        _, payload = mock_executor.submit.call_args[0]
        assert payload["ip_address"] == ""
