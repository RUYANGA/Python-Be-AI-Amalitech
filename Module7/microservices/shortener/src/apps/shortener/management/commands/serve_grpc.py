"""Runs the shortener service's internal gRPC server.

A long-lived process (a separate container — see ``shortener-grpc`` in
``docker-compose.yml``) that serves the ``urlownership.ShortenerOwnership``
contract to the analytics service. It shares the app's Django settings but
serves no HTTP; the web ``uvicorn`` process continues to handle client
traffic on its own port.

Command: ``python manage.py serve_grpc --port 50051``
"""

from __future__ import annotations

import logging
from concurrent import futures

import grpc
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.shortener.api.grpc.servicer import OwnershipServicer
from apps.shortener.api.services import build_url_service
from urlownership import ownership_pb2_grpc

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the shortener internal gRPC ownership server."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=50051)
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument(
            "--noreload",
            action="store_true",
            help="Disable the auto-reloader (used by the non-dev entrypoint).",
        )

    def handle(self, *_args, **options):
        host = options["host"]
        port = options["port"]
        url_service = build_url_service()
        servicer = OwnershipServicer(
            url_service=url_service,
            internal_token=settings.INTERNAL_SERVICE_TOKEN,
        )

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=options["workers"]))
        ownership_pb2_grpc.add_ShortenerOwnershipServicer_to_server(servicer, server)
        address = f"{host}:{port}"
        server.add_insecure_port(address)
        server.start()
        self.stdout.write(self.style.SUCCESS(f"serve_grpc: listening on {address}"))
        server.wait_for_termination()
