#!/usr/bin/env bash
# Usage: ./run.sh [backend|frontend|all]   (default: all)
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || { echo "Create the virtualenv first (see README: Installation)"; exit 1; }
source .venv/bin/activate
[ -f .env ] || { echo "Missing .env - run: cp .env.example .env and set SECRET_KEY"; exit 1; }
case "${1:-all}" in
  backend)  exec uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 ;;
  frontend) exec streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501 ;;
  all)
    uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
    BACK=$!; trap 'kill $BACK 2>/dev/null' EXIT
    sleep 3
    streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501 ;;
  *) echo "usage: $0 [backend|frontend|all]"; exit 1 ;;
esac
