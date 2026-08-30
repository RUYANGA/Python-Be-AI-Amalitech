"""Unit tests for the shortener API's custom permission classes."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from django.http import Http404

from apps.shortener.api.permissions import IsOwnerOrReadOnly


class TestIsOwnerOrReadOnly:
    def setup_method(self) -> None:
        self.permission = IsOwnerOrReadOnly()
        self.owner = Mock(id=1)
        self.obj = Mock(owner_id=1)

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_safe_methods_are_always_allowed(self, method):
        request = Mock(method=method, user=Mock(id=2))

        assert self.permission.has_object_permission(request, Mock(), self.obj) is True

    @pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
    def test_owner_can_write(self, method):
        request = Mock(method=method, user=self.owner)

        assert self.permission.has_object_permission(request, Mock(), self.obj) is True

    @pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
    def test_non_owner_write_raises_404_not_403(self, method):
        request = Mock(method=method, user=Mock(id=2))

        with pytest.raises(Http404):
            self.permission.has_object_permission(request, Mock(), self.obj)
