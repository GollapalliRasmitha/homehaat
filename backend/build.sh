#!/usr/bin/env bash
# Render runs this at every deploy (Build Command: ./build.sh, root directory: backend).
# Free Render services have no shell and no pre-deploy step, so the database is migrated here.
set -o errexit  # stop at the first failing step: a broken deploy never goes live

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input   # the admin's CSS/JS, served by WhiteNoise
python manage.py migrate --no-input          # only adds what's new; never deletes data
python manage.py seed_categories             # the fixed category list (safe to run again)
python manage.py ensure_admin                # the admin account, if DJANGO_ADMIN_EMAIL/PASSWORD are set
python manage.py check --deploy --fail-level ERROR
