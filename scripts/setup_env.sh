#!/usr/bin/env bash
# Creates .env from .env.example with a fresh SECRET_KEY and admin credentials.
# Usage: ./scripts/setup_env.sh you@example.com ["Your Name"]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env already exists - not overwriting."; exit 1; }
EMAIL="${1:?Usage: $0 admin-email [full name]}"
NAME="${2:-System Administrator}"
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(14) + '#1')")
cp .env.example .env
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|; s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${EMAIL}|; s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${PASS}|; s|^ADMIN_FULL_NAME=.*|ADMIN_FULL_NAME=${NAME}|" .env
chmod 600 .env
echo ".env created."
echo "Admin login ->  email: ${EMAIL}   password: ${PASS}"
echo "Save this password now; change it in Profile after first login."
