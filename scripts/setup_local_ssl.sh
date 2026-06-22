#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT_DIR="$ROOT/certs"
CERT_FILE="$CERT_DIR/readbase-local.pem"
KEY_FILE="$CERT_DIR/readbase-local-key.pem"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert is required. Install with: brew install mkcert"
  exit 1
fi

echo "Installing mkcert local CA (requires your macOS password once)..."
mkcert -install

mkdir -p "$CERT_DIR"
mkcert -cert-file "$CERT_FILE" -key-file "$KEY_FILE" localhost 127.0.0.1

cat <<EOF

Local HTTPS certificates created:
  $CERT_FILE
  $KEY_FILE

Add or update these in your .env:

READBASE_SSL_CERTFILE=certs/readbase-local.pem
READBASE_SSL_KEYFILE=certs/readbase-local-key.pem
APP_BASE_URL=https://127.0.0.1:8000
APP_SESSION_COOKIE_SECURE=true
SLACK_REDIRECT_URI=https://127.0.0.1:8000/api/me/integrations/slack/callback

Also switch other *_REDIRECT_URI values from http:// to https://127.0.0.1:8000/...

In Slack app settings (OAuth & Permissions), add redirect URL:
  https://127.0.0.1:8000/api/me/integrations/slack/callback

Then restart Readbase and open: https://127.0.0.1:8000
EOF
