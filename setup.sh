#!/usr/bin/env bash
# One-shot local setup (works in Termux proot-distro Ubuntu). Uses SQLite unless DATABASE_URL is set.
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
[ -n "$(ls listings/migrations | grep -v -e __init__ -e __pycache__ || true)" ] || python manage.py makemigrations listings
python manage.py migrate
python manage.py seed_demo
pytest -q || echo "Some tests failed: copy the output and send it to me."
echo
echo "Create an admin user:   python manage.py createsuperuser"
echo "Start the server:       uvicorn api.main:app --host 127.0.0.1 --port 8000"
