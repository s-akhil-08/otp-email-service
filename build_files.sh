#!/usr/bin/env bash
set -o errexit

# Install dependencies
python3 -m pip install -r requirements.txt

# Collect static files
python3 manage.py collectstatic --noinput --clear

# Run migrations
python3 manage.py migrate
