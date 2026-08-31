"""Runs the auth service's internal gRPC token-validation server.

A long-lived process (a separate container — see ``auth-grpc`` in
``docker-compose.yml``) that serves the ``authtoken.AuthTokenValidation``
contract to the shortener and analytics services. It shares the app's
Django settings but serves no HTTP; the web ``uvicorn`` process continues
to handle client traffic on its own port.

Command: ``python manage.py serve_grpc --port 50052``
"""

from __future__ import annotations

import logging
from concurrent import futures

import grpc
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.users.api.grpc.servicer import AuthTokenValidationServicer
from authtoken import authtoken_pb2_grpc

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the auth service's internal gRPC token-validation server."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=50052)
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument(
            "--noreload",
            action="store_true",
            help="Disable the auto-reloader (used by the non-dev entrypoint).",
        )

    def handle(self, *_args, **options):
        host = options["host"]
        port = options["port"]
        servicer = AuthTokenValidationServicer(internal_token=settings.INTERNAL_SERVICE_TOKEN)

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=options["workers"]))
        authtoken_pb2_grpc.add_AuthTokenValidationServicer_to_server(servicer, server)
        address = f"{host}:{port}"
        server.add_insecure_port(address)
        server.start()
        self.stdout.write(self.style.SUCCESS(f"serve_grpc: listening on {address}"))
        server.wait_for_termination()
