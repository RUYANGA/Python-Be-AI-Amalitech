#!/usr/bin/env bash
# Generates the RS256 keypair used for cross-service JWT verification.
#
# The private key is used only by the auth service to *sign* tokens and
# must never leave it. The public key is not secret — it is copied into
# the shortener and analytics services (at build time) so they can
# *verify* a token's signature locally, with no network call back to
# auth on every request.
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p keys
openssl genrsa -out keys/jwt-private.pem 2048
openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem

chmod 600 keys/jwt-private.pem
chmod 644 keys/jwt-public.pem

echo "Wrote keys/jwt-private.pem (auth service only) and keys/jwt-public.pem (shared)."
